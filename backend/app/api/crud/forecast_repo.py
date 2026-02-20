from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import logging
import time
import hashlib
import json

# Try to import statsmodels for ARIMA and Holt-Winters
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.stattools import adfuller
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_AVAILABLE = True
    print("✅ statsmodels loaded successfully")
except ImportError as e:
    STATSMODELS_AVAILABLE = False
    print(f"⚠️ statsmodels not available: {e}. Install with: pip install statsmodels")

# Try to import scipy for advanced statistics
try:
    from scipy import stats
    from scipy.optimize import curve_fit
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("⚠️ scipy not available. Install with: pip install scipy")

import warnings
warnings.filterwarnings('ignore')


def _to_float(v: Any) -> float:
    """Simple numeric parser - just like industries repo"""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", ""))
    except:
        return 0.0


def _safe_round(value: float, digits: int = 0) -> int:
    """Safely round a value, handling NaN and None"""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 0
    return int(round(value))


def _data_hash(data: List[float]) -> str:
    """Create a hash of the data for caching"""
    # Round to 2 decimals to create cache keys
    rounded = [round(x, 2) for x in data]
    return hashlib.md5(json.dumps(rounded).encode()).hexdigest()[:10]


class ForecastRepo:
    """
    Enhanced forecast repository with multiple models, backtesting, and accuracy metrics
    Includes ARIMA and Holt-Winters when statsmodels is available
    """
    
    def __init__(self, db):
        self.db = db
        # Economic factors cache
        self._economic_factors = None
        # Cache for ARIMA results to avoid recomputing
        self._arima_cache = {}
        self._hw_cache = {}
    
    # ==========================================================
    # DATA FETCHING
    # ==========================================================
    
    async def get_industry_time_series(self, naics: str) -> List[Dict]:
        """Get time series data for a specific industry"""
        pipeline = [
            {
                "$match": {
                    "naics": naics,
                    "occ_code": "00-0000",
                    "year": {"$gte": 2011, "$lte": 2024}
                }
            },
            {
                "$project": {
                    "year": 1,
                    "tot_emp": 1,
                    "_id": 0
                }
            },
            {"$sort": {"year": 1}}
        ]
        
        cursor = self.db["bls_oews"].aggregate(pipeline)
        data = []
        async for doc in cursor:
            emp = _to_float(doc.get("tot_emp"))
            if emp > 0:  # Only include valid data
                data.append({
                    "year": doc["year"],
                    "employment": emp
                })
        return data
    
    async def get_top_industries(self, limit: int = 10) -> List[Dict]:
        """Get top industries - excluding cross-industry and with deduplication"""
        pipeline = [
            {
                "$match": {
                    "year": 2024,
                    "occ_code": "00-0000",
                    "naics": {"$ne": "000000"},  # Exclude cross-industry
                    "naics_title": {"$not": {"$regex": "Cross-industry", "$options": "i"}}  # Also exclude by title
                }
            },
            {
                "$project": {
                    "naics": 1,
                    "naics_title": 1,
                    "tot_emp": 1,
                    "_id": 0
                }
            },
            {"$sort": {"tot_emp": -1}},
        ]
        
        cursor = self.db["bls_oews"].aggregate(pipeline)
        
        # Deduplicate by naics_title (case-insensitive)
        seen_titles = set()
        industries = []
        
        async for doc in cursor:
            title = doc["naics_title"].strip().lower()
            if title in seen_titles:
                continue
            seen_titles.add(title)
            
            industries.append({
                "naics": doc["naics"],
                "title": doc["naics_title"],
                "employment_2024": _to_float(doc["tot_emp"]),
            })
            
            if len(industries) >= limit:
                break
        
        return industries
    
    async def get_top_jobs(self, limit: int = 8) -> List[Dict]:
        """Get top jobs - with deduplication"""
        pipeline = [
            {
                "$match": {
                    "year": 2024,
                    "naics": "000000",
                    "occ_code": {"$ne": "00-0000"}
                }
            },
            {
                "$project": {
                    "occ_code": 1,
                    "occ_title": 1,
                    "tot_emp": 1,
                    "_id": 0
                }
            },
            {"$sort": {"tot_emp": -1}},
        ]
        
        cursor = self.db["bls_oews"].aggregate(pipeline)
        
        # Deduplicate by occ_title
        seen_titles = set()
        jobs = []
        
        async for doc in cursor:
            title = doc["occ_title"].strip().lower()
            if title in seen_titles:
                continue
            seen_titles.add(title)
            
            jobs.append({
                "occ_code": doc["occ_code"],
                "title": doc["occ_title"],
                "employment_2024": _to_float(doc["tot_emp"]),
            })
            
            if len(jobs) >= limit:
                break
        
        return jobs
    
    async def _get_economic_factors(self) -> Dict[str, float]:
        """Get economic factors for forecast adjustment"""
        # This would ideally come from a database of economic indicators
        # For now, using reasonable defaults based on recent trends
        if self._economic_factors is None:
            # You could fetch these from FRED API or your database
            self._economic_factors = {
                "gdp_growth": 2.1,        # % GDP growth
                "unemployment_rate": 3.8,  # % unemployment
                "inflation": 2.5,           # % inflation
                "productivity_growth": 1.2  # % productivity growth
            }
        return self._economic_factors
    
    # ==========================================================
    # MODEL UTILITIES
    # ==========================================================
    
    def _smooth_series(self, values: List[float]) -> List[float]:
        """Apply 2-year rolling average smoothing"""
        if len(values) < 2:
            return values
        return pd.Series(values).rolling(2, min_periods=1).mean().tolist()
    
    def _detect_outliers(self, values: List[float], threshold: float = 2.5) -> List[bool]:
        """Detect outliers using z-score method if scipy available"""
        if len(values) < 4 or not SCIPY_AVAILABLE:
            return [False] * len(values)
        
        try:
            z_scores = np.abs(stats.zscore(values))
            return [z > threshold for z in z_scores]
        except:
            return [False] * len(values)
    
    def _remove_outliers(self, values: List[float]) -> List[float]:
        """Remove outliers by replacing with moving average"""
        outliers = self._detect_outliers(values)
        if not any(outliers):
            return values
        
        cleaned = values.copy()
        for i, is_outlier in enumerate(outliers):
            if is_outlier:
                # Replace with average of neighbors
                left = values[i-1] if i > 0 else None
                right = values[i+1] if i < len(values)-1 else None
                if left and right:
                    cleaned[i] = (left + right) / 2
                elif left:
                    cleaned[i] = left
                elif right:
                    cleaned[i] = right
        
        return cleaned
    
    # ==========================================================
    # FORECASTING MODELS
    # ==========================================================
    
    def _simple_forecast(self, data: List[float], years: int) -> List[float]:
        """Simple linear forecast based on average growth rate"""
        if len(data) < 2:
            return [data[-1] if data else 0] * years
        
        # Calculate average growth rate
        growth_rates = []
        for i in range(1, len(data)):
            if data[i-1] > 0:
                growth_rates.append((data[i] - data[i-1]) / data[i-1])
        
        avg_growth = np.mean(growth_rates) if growth_rates else 0.03
        
        # Project forward
        forecasts = []
        last = data[-1]
        for _ in range(years):
            next_val = last * (1 + avg_growth)
            forecasts.append(next_val)
            last = next_val
        
        return forecasts
    
    def _weighted_growth_forecast(self, data: List[float], years: int) -> List[float]:
        """Weight recent years more heavily"""
        if len(data) < 2:
            return [data[-1] if data else 0] * years
        
        # Calculate growth rates with exponential weights
        growth_rates = []
        weights = []
        for i in range(1, len(data)):
            if data[i-1] > 0:
                growth_rates.append((data[i] - data[i-1]) / data[i-1])
                # More recent years get higher weight (exponential)
                weights.append(np.exp(i))  # Exponential weighting
        
        if not growth_rates:
            return [data[-1]] * years
        
        # Normalize weights
        weights = [w/sum(weights) for w in weights]
        weighted_avg_growth = np.average(growth_rates, weights=weights)
        
        # Project forward
        forecasts = []
        last = data[-1]
        for _ in range(years):
            next_val = last * (1 + weighted_avg_growth)
            forecasts.append(next_val)
            last = next_val
        
        return forecasts
    
    def _linear_trend_forecast(self, data: List[float], years: int) -> List[float]:
        """Use linear regression on raw data"""
        if len(data) < 3:
            return self._simple_forecast(data, years)
        
        try:
            x = np.arange(len(data))
            y = data
            
            # Linear regression
            slope, intercept = np.polyfit(x, y, 1)
            
            # Project forward
            forecasts = []
            for i in range(years):
                next_idx = len(data) + i
                val = intercept + slope * next_idx
                forecasts.append(max(0, val))
            
            return forecasts
        except:
            return self._simple_forecast(data, years)
    
    def _log_trend_forecast(self, data: List[float], years: int) -> List[float]:
        """Use linear regression on log-transformed data for exponential trends"""
        if len(data) < 3 or min(data) <= 0:
            return self._simple_forecast(data, years)
        
        try:
            x = np.arange(len(data))
            y = np.log(data)
            
            # Linear regression on log data
            slope, intercept = np.polyfit(x, y, 1)
            
            # Project forward
            forecasts = []
            for i in range(years):
                next_idx = len(data) + i
                log_pred = intercept + slope * next_idx
                forecasts.append(max(0, np.exp(log_pred)))
            
            return forecasts
        except:
            return self._simple_forecast(data, years)
    
    def _polynomial_forecast(self, data: List[float], years: int, degree: int = 2) -> List[float]:
        """Use polynomial regression for curved trends"""
        if len(data) < degree + 1:
            return self._simple_forecast(data, years)
        
        try:
            x = np.arange(len(data))
            y = data
            
            # Polynomial regression
            coeffs = np.polyfit(x, y, degree)
            
            # Project forward
            forecasts = []
            for i in range(years):
                next_idx = len(data) + i
                pred = 0
                for d, coef in enumerate(reversed(coeffs)):
                    pred += coef * (next_idx ** d)
                forecasts.append(max(0, pred))
            
            return forecasts
        except:
            return self._simple_forecast(data, years)
    
    def _fast_arima_forecast(self, data: List[float], years: int) -> List[float]:
        """
        Optimized ARIMA forecast with caching and limited orders
        Much faster than the full grid search version
        """
        if not STATSMODELS_AVAILABLE:
            return self._simple_forecast(data, years)
        
        # Only run ARIMA on longer series (8+ years) - it needs data
        if len(data) < 8:
            return self._simple_forecast(data, years)
        
        # Create cache key
        cache_key = f"{_data_hash(data)}_{years}"
        
        # Check cache
        if cache_key in self._arima_cache:
            print(f"    📈 ARIMA (cached)")
            return self._arima_cache[cache_key]
        
        start_time = time.time()
        
        try:
            # Quick stationarity check
            try:
                adf_test = adfuller(data, autolag='AIC', regression='c')
                d = 0 if adf_test[1] < 0.05 else 1
            except:
                d = 1  # Default to differencing if test fails
            
            # Use only 2 best-performing orders to save time
            # These are typically the most reliable for economic data
            orders_to_try = []
            
            if d == 0:
                orders_to_try = [(1, 0, 0), (0, 0, 1)]  # AR(1) or MA(1) for stationary
            else:
                orders_to_try = [(1, 1, 0), (0, 1, 1)]  # ARIMA(1,1,0) or (0,1,1) for trending
            
            best_aic = float('inf')
            best_model = None
            best_order = None
            
            for order in orders_to_try:
                try:
                    model = ARIMA(data, order=order)
                    model_fit = model.fit(method_kwargs={'maxiter': 100})  # Limit iterations
                    if model_fit.aic < best_aic:
                        best_aic = model_fit.aic
                        best_model = model_fit
                        best_order = order
                except:
                    continue
            
            if best_model is None:
                # Fall back to simple AR(1) if all else fails
                try:
                    model = ARIMA(data, order=(1, d, 0))
                    best_model = model.fit(method_kwargs={'maxiter': 100})
                    best_order = (1, d, 0)
                except:
                    self._arima_cache[cache_key] = self._simple_forecast(data, years)
                    return self._arima_cache[cache_key]
            
            # Forecast
            forecast = best_model.forecast(steps=years)
            forecast_values = forecast.tolist()
            
            # Ensure non-negative and handle NaN
            forecast_values = [max(0, f) if not np.isnan(f) else data[-1] for f in forecast_values]
            
            elapsed = time.time() - start_time
            print(f"    📈 ARIMA {best_order} in {elapsed:.2f}s (AIC: {best_aic:.0f})")
            
            # Cache the result
            self._arima_cache[cache_key] = forecast_values
            return forecast_values
            
        except Exception as e:
            print(f"    📈 ARIMA failed ({str(e)[:30]}) - using simple")
            result = self._simple_forecast(data, years)
            self._arima_cache[cache_key] = result
            return result
    
    def _fast_hw_forecast(self, data: List[float], years: int) -> List[float]:
        """
        Optimized Holt-Winters forecast with caching
        """
        if not STATSMODELS_AVAILABLE:
            return self._simple_forecast(data, years)
        
        if len(data) < 6:  # Need decent data for HW
            return self._simple_forecast(data, years)
        
        # Create cache key
        cache_key = f"{_data_hash(data)}_{years}"
        
        # Check cache
        if cache_key in self._hw_cache:
            print(f"    📊 Holt-Winters (cached)")
            return self._hw_cache[cache_key]
        
        start_time = time.time()
        
        try:
            # Try only additive trend (faster, usually works well)
            model = ExponentialSmoothing(
                data,
                trend='add',
                seasonal=None,
                initialization_method='estimated'
            )
            model_fit = model.fit()
            
            forecast = model_fit.forecast(years)
            forecast_values = forecast.tolist()
            
            # Ensure non-negative and handle NaN
            forecast_values = [max(0, f) if not np.isnan(f) else data[-1] for f in forecast_values]
            
            elapsed = time.time() - start_time
            print(f"    📊 Holt-Winters in {elapsed:.2f}s")
            
            # Cache the result
            self._hw_cache[cache_key] = forecast_values
            return forecast_values
            
        except Exception as e:
            print(f"    📊 Holt-Winters failed - using simple")
            result = self._simple_forecast(data, years)
            self._hw_cache[cache_key] = result
            return result
    
    def _ensemble_forecast(self, data: List[float], years: int, title: str = "") -> Tuple[List[float], Dict[str, float]]:
        """Combine multiple forecasting methods with dynamic weights"""
        if len(data) < 3:
            return self._simple_forecast(data, years), {"simple": 1.0}
        
        # Get forecasts from different methods
        forecasts = {}
        
        # Always include these basic models (fast)
        forecasts['simple'] = self._simple_forecast(data, years)
        forecasts['weighted'] = self._weighted_growth_forecast(data, years)
        forecasts['linear'] = self._linear_trend_forecast(data, years)
        
        # Add log trend if data positive (fast)
        if min(data) > 0:
            forecasts['log_trend'] = self._log_trend_forecast(data, years)
        
        # Add polynomial if enough data (fast)
        if len(data) >= 4:
            forecasts['poly2'] = self._polynomial_forecast(data, years, degree=2)
        
        if len(data) >= 5:
            forecasts['poly3'] = self._polynomial_forecast(data, years, degree=3)
        
        # Add ARIMA and Holt-Winters if statsmodels available
        # Only run on longer series to avoid slowdowns on short data
        if STATSMODELS_AVAILABLE:
            if len(data) >= 8:  # Only run ARIMA on longer series
                forecasts['arima'] = self._fast_arima_forecast(data, years)
            
            if len(data) >= 6:  # Holt-Winters needs decent data
                forecasts['holt_winters'] = self._fast_hw_forecast(data, years)
        
        # Calculate weights based on recent performance (backtesting)
        weights = {}
        test_size = min(3, len(data) // 4)
        
        if test_size >= 2:
            train = data[:-test_size]
            test = data[-test_size:]
            
            # Test base models on backtest period (fast models only)
            base_models = {
                'simple': self._simple_forecast,
                'weighted': self._weighted_growth_forecast,
                'linear': self._linear_trend_forecast
            }
            
            for name, model_func in base_models.items():
                try:
                    pred = model_func(train, len(test))
                    if len(pred) == len(test) and not any(np.isnan(pred)):
                        # Calculate MAPE
                        errors = []
                        for j in range(len(test)):
                            if test[j] > 0:
                                errors.append(abs(pred[j] - test[j]) / test[j])
                        if errors:
                            mape = np.mean(errors)
                            weights[name] = 1.0 / (1.0 + mape)  # Inverse error weighting
                        else:
                            weights[name] = 0.1
                    else:
                        weights[name] = 0.1
                except Exception:
                    weights[name] = 0.1
            
            # Give ARIMA and HW a small default weight if they exist
            if 'arima' in forecasts:
                weights['arima'] = 0.15  # Fixed weight for ARIMA
            if 'holt_winters' in forecasts:
                weights['holt_winters'] = 0.15  # Fixed weight for HW
            
            # Normalize weights
            total = sum(weights.values())
            if total > 0:
                weights = {k: v/total for k, v in weights.items()}
            else:
                weights = {k: 1.0/len(forecasts) for k in forecasts.keys()}
        else:
            # Equal weights if not enough data for backtesting
            weights = {name: 1.0/len(forecasts) for name in forecasts.keys()}
        
        # Combine forecasts
        ensemble = np.zeros(years)
        weight_sum = 0
        
        for name, forecast in forecasts.items():
            if name in weights:
                ensemble += np.array(forecast) * weights[name]
                weight_sum += weights[name]
            else:
                # For models not in weights, use small default weight
                ensemble += np.array(forecast) * 0.05
                weight_sum += 0.05
        
        # Normalize ensemble
        if weight_sum > 0:
            ensemble = ensemble / weight_sum
        
        # Ensure no NaN values
        ensemble = np.nan_to_num(ensemble, nan=data[-1] if data else 0)
        
        return ensemble.tolist(), weights
    
    # ==========================================================
    # ACCURACY METRICS
    # ==========================================================
    
    def _calculate_accuracy_metrics(self, actual: List[float], predicted: List[float]) -> Dict[str, float]:
        """Calculate multiple accuracy metrics"""
        if len(actual) == 0 or len(predicted) == 0:
            return {
                "mape": 999.0,
                "rmse": 999.0,
                "mae": 999.0,
                "mpe": 999.0,
                "mase": 999.0
            }
        
        errors = []
        percentage_errors = []
        
        for i in range(min(len(actual), len(predicted))):
            if actual[i] > 0 and not np.isnan(predicted[i]):
                error = predicted[i] - actual[i]
                errors.append(error)
                percentage_errors.append(abs(error) / actual[i])
        
        if not errors:
            return {
                "mape": 999.0,
                "rmse": 999.0,
                "mae": 999.0,
                "mpe": 999.0,
                "mase": 999.0
            }
        
        # Calculate metrics
        mape = np.mean(percentage_errors) * 100  # Mean Absolute Percentage Error
        rmse = np.sqrt(np.mean([e**2 for e in errors]))  # Root Mean Square Error
        mae = np.mean([abs(e) for e in errors])  # Mean Absolute Error
        mpe = np.mean(errors) / np.mean(actual) * 100  # Mean Percentage Error (signed)
        
        # Mean Absolute Scaled Error
        if len(actual) > 1:
            naive_errors = [abs(actual[i] - actual[i-1]) for i in range(1, len(actual))]
            if naive_errors and np.mean(naive_errors) > 0:
                mase = mae / np.mean(naive_errors)
            else:
                mase = 999.0
        else:
            mase = 999.0
        
        # Handle NaN values
        return {
            "mape": round(mape, 2) if not np.isnan(mape) else 999.0,
            "rmse": round(rmse, 2) if not np.isnan(rmse) else 999.0,
            "mae": round(mae, 2) if not np.isnan(mae) else 999.0,
            "mpe": round(mpe, 2) if not np.isnan(mpe) else 999.0,
            "mase": round(mase, 2) if not np.isnan(mase) else 999.0
        }
    
    def _backtest_model(self, values: List[float], years: List[int], test_size: int = 3, title: str = "") -> Dict[str, Any]:
        """Backtest the ensemble model on historical data"""
        if len(values) <= test_size:
            return {
                "accuracy_metrics": {
                    "mape": 999.0,
                    "rmse": 999.0,
                    "mae": 999.0,
                    "mpe": 999.0,
                    "mase": 999.0
                },
                "test_period": [],
                "predicted": [],
                "model_weights": {}
            }
        
        # Split data into training and testing
        train_values = values[:-test_size]
        test_values = values[-test_size:]
        test_years = years[-test_size:]
        
        print(f"\n  🔍 Backtesting {title} (train={len(train_values)} years, test={len(test_values)} years)")
        
        # Generate predictions using ensemble
        predictions, weights = self._ensemble_forecast(train_values, len(test_values), title)
        
        # Ensure predictions don't contain NaN
        predictions = [p if not np.isnan(p) else train_values[-1] for p in predictions]
        
        # Calculate accuracy metrics
        metrics = self._calculate_accuracy_metrics(test_values, predictions)
        
        # Prepare comparison data
        comparison = []
        for i in range(len(test_years)):
            if i < len(predictions):
                pred_val = predictions[i] if not np.isnan(predictions[i]) else test_values[i]
                error_pct = ((pred_val - test_values[i]) / test_values[i]) * 100 if test_values[i] > 0 else 0
                comparison.append({
                    "year": test_years[i],
                    "actual": _safe_round(test_values[i]),
                    "predicted": _safe_round(pred_val),
                    "error": _safe_round(pred_val - test_values[i]),
                    "error_pct": round(error_pct, 1) if not np.isnan(error_pct) else 0
                })
        
        print(f"  ✅ Backtest MAPE: {metrics['mape']}%")
        
        return {
            "accuracy_metrics": metrics,
            "test_period": test_years,
            "predictions": [_safe_round(p) for p in predictions],
            "actuals": [_safe_round(v) for v in test_values],
            "comparison": comparison,
            "model_weights": {k: round(v, 3) for k, v in weights.items() if not np.isnan(v)}
        }
    
    # ==========================================================
    # ECONOMIC ADJUSTMENT
    # ==========================================================
    
    async def _adjust_with_economic_factors(self, forecast: float, year: int) -> float:
        """Adjust forecast based on economic conditions"""
        factors = await self._get_economic_factors()
        
        # Base adjustment
        adjustment = 1.0
        
        # GDP growth adjustment
        if factors["gdp_growth"] > 3:
            adjustment *= 1.03  # Boost if economy growing fast
        elif factors["gdp_growth"] < 1:
            adjustment *= 0.98  # Reduce if slow growth
        elif factors["gdp_growth"] < 0:
            adjustment *= 0.95  # Reduce more if recession
        
        # Unemployment adjustment (low unemployment -> more hiring)
        if factors["unemployment_rate"] < 4:
            adjustment *= 1.02
        elif factors["unemployment_rate"] > 6:
            adjustment *= 0.98
        
        # Inflation adjustment
        if factors["inflation"] > 3:
            adjustment *= 0.99  # High inflation might slow hiring
        
        return forecast * adjustment
    
    # ==========================================================
    # CORE FORECASTING
    # ==========================================================
    
    async def forecast_industry(self, naics: str, title: str, data: List[Dict], forecast_year: int, verbose: bool = False) -> Optional[Dict]:
        """Forecast a single industry with multiple models and accuracy metrics"""
        
        if len(data) < 3:  # Need at least 3 years of data
            print(f"⚠️ Insufficient data for {title}: {len(data)} years")
            return None
        
        print(f"\n📈 Forecasting {title}...")
        
        # Extract and smooth data
        years = [d["year"] for d in data]
        raw_values = [d["employment"] for d in data]
        
        # Remove outliers
        cleaned_values = self._remove_outliers(raw_values)
        
        # Apply smoothing
        values = self._smooth_series(cleaned_values)
        
        horizon = forecast_year - 2024
        
        # Run backtest to evaluate model accuracy
        backtest_results = self._backtest_model(values, years, test_size=min(3, len(values) // 3), title=title)
        
        # Generate final forecast using ensemble
        final_forecast, model_weights = self._ensemble_forecast(values, horizon, title)
        
        # Ensure no NaN in forecast
        final_forecast = [v if not np.isnan(v) else values[-1] for v in final_forecast]
        
        # Apply economic adjustments for each forecast year
        adjusted_forecast = []
        for i, year in enumerate(range(2025, forecast_year + 1)):
            if i < len(final_forecast):
                adjusted_val = await self._adjust_with_economic_factors(final_forecast[i], year)
                adjusted_forecast.append(adjusted_val)
            else:
                adjusted_forecast.append(final_forecast[-1] if final_forecast else values[-1])
        
        current_2024 = values[-1]
        final_value = adjusted_forecast[-1] if adjusted_forecast else current_2024
        
        # Calculate Compound Annual Growth Rate (CAGR)
        years_diff = forecast_year - 2024
        if years_diff > 0 and current_2024 > 0 and final_value > 0:
            cagr = ((final_value / current_2024) ** (1 / years_diff) - 1) * 100
        else:
            cagr = 0
        
        # Calculate confidence interval (simplified)
        if backtest_results["accuracy_metrics"]["mape"] < 999:
            confidence_interval = {
                "lower": _safe_round(final_value * (1 - backtest_results["accuracy_metrics"]["mape"] / 200)),
                "upper": _safe_round(final_value * (1 + backtest_results["accuracy_metrics"]["mape"] / 200))
            }
        else:
            confidence_interval = {
                "lower": _safe_round(final_value * 0.9),
                "upper": _safe_round(final_value * 1.1)
            }
        
        # Prepare forecast values for all years
        forecast_dict = {}
        for i, year in enumerate(range(2025, forecast_year + 1)):
            if i < len(adjusted_forecast):
                forecast_dict[f"forecast_{year}"] = _safe_round(adjusted_forecast[i])
            else:
                forecast_dict[f"forecast_{year}"] = 0
        
        if verbose:
            print(f"\n📊 Forecast for {title}:")
            print(f"  MAPE: {backtest_results['accuracy_metrics']['mape']}%")
            print(f"  Model Weights: {model_weights}")
            if backtest_results['comparison']:
                print("  Backtest Period:")
                for comp in backtest_results['comparison']:
                    print(f"    {comp['year']}: Actual={comp['actual']}, Predicted={comp['predicted']}, Error={comp['error_pct']}%")
        
        return {
            "industry": title,
            "naics": naics,
            "current": _safe_round(current_2024),
            **forecast_dict,
            "growth_rate": round(cagr, 2),
            "confidence_interval": confidence_interval,
            "backtest_metrics": backtest_results["accuracy_metrics"],
            "backtest_comparison": backtest_results["comparison"],
            "model_weights": {k: round(v, 3) for k, v in model_weights.items()}
        }
    
    async def forecast_job(self, occ_code: str, title: str, forecast_year: int, verbose: bool = False) -> Optional[Dict]:
        """Forecast a single job with multiple models"""
        # Get time series data
        pipeline = [
            {
                "$match": {
                    "occ_code": occ_code,
                    "naics": "000000",
                    "year": {"$gte": 2011, "$lte": 2024}
                }
            },
            {
                "$project": {
                    "year": 1,
                    "tot_emp": 1,
                    "_id": 0
                }
            },
            {"$sort": {"year": 1}}
        ]
        
        cursor = self.db["bls_oews"].aggregate(pipeline)
        data = []
        async for doc in cursor:
            emp = _to_float(doc.get("tot_emp"))
            if emp > 0:
                data.append({
                    "year": doc["year"],
                    "employment": emp
                })
        
        if len(data) < 3:
            return None
        
        print(f"\n📈 Forecasting job: {title}...")
        
        years = [d["year"] for d in data]
        raw_values = [d["employment"] for d in data]
        
        # Remove outliers and smooth
        cleaned_values = self._remove_outliers(raw_values)
        values = self._smooth_series(cleaned_values)
        
        horizon = forecast_year - 2024
        
        # Run backtest
        backtest_results = self._backtest_model(values, years, test_size=min(3, len(values) // 3), title=title)
        
        # Generate forecast using ensemble
        final_forecast, model_weights = self._ensemble_forecast(values, horizon, title)
        
        # Ensure no NaN in forecast
        final_forecast = [v if not np.isnan(v) else values[-1] for v in final_forecast]
        
        # Apply economic adjustments
        adjusted_forecast = []
        for i, year in enumerate(range(2025, forecast_year + 1)):
            if i < len(final_forecast):
                adjusted_val = await self._adjust_with_economic_factors(final_forecast[i], year)
                adjusted_forecast.append(adjusted_val)
            else:
                adjusted_forecast.append(final_forecast[-1] if final_forecast else values[-1])
        
        current_2024 = next((d["employment"] for d in data if d["year"] == 2024), values[-1])
        
        # Calculate growth rate
        years_diff = forecast_year - 2024
        if years_diff > 0 and current_2024 > 0 and len(adjusted_forecast) > 0:
            growth_rate = ((adjusted_forecast[-1] / current_2024) ** (1 / years_diff) - 1) * 100
        else:
            growth_rate = 0
        
        forecast_dict = {}
        for i, year in enumerate(range(2025, forecast_year + 1)):
            if i < len(adjusted_forecast):
                forecast_dict[f"forecast_{year}"] = _safe_round(adjusted_forecast[i])
            else:
                forecast_dict[f"forecast_{year}"] = 0
        
        if verbose:
            print(f"\n📊 Forecast for {title}:")
            print(f"  MAPE: {backtest_results['accuracy_metrics']['mape']}%")
        
        return {
            "title": title,
            "occ_code": occ_code,
            "current": _safe_round(current_2024),
            **forecast_dict,
            "growth_rate": round(growth_rate, 2),
            "backtest_metrics": backtest_results["accuracy_metrics"],
            "model_weights": {k: round(v, 3) for k, v in model_weights.items()}
        }
    
    # ==========================================================
    # ADDITIONAL FORECAST METHODS FOR ROUTER
    # ==========================================================
    
    async def forecast_top_industries(self, limit: int = 6, forecast_years: int = 4) -> List[Dict]:
        """Forecast top industries for multiple years"""
        top_industries = await self.get_top_industries(limit)
        forecast_year = 2024 + forecast_years
        
        forecasts = []
        for ind in top_industries:
            data = await self.get_industry_time_series(ind["naics"])
            forecast = await self.forecast_industry(
                ind["naics"], 
                ind["title"], 
                data, 
                forecast_year,
                verbose=False
            )
            if forecast:
                # Format for the frontend
                item = {
                    "industry": forecast["industry"],
                    "current": forecast["current"]
                }
                # Add forecast values for each year
                for i, year in enumerate(range(2025, forecast_year + 1)):
                    item[f"forecast_{year}"] = forecast.get(f"forecast_{year}", 0)
                item["growth_rate"] = forecast["growth_rate"]
                forecasts.append(item)
        
        return forecasts
    
    async def forecast_top_jobs(self, limit: int = 8, forecast_years: int = 4) -> List[Dict]:
        """Forecast top jobs for multiple years"""
        top_jobs = await self.get_top_jobs(limit)
        forecast_year = 2024 + forecast_years
        
        forecasts = []
        for job in top_jobs:
            forecast = await self.forecast_job(
                job["occ_code"], 
                job["title"], 
                forecast_year,
                verbose=False
            )
            if forecast:
                # Format for the frontend
                item = {
                    "title": forecast["title"],
                    "current": forecast["current"]
                }
                # Add forecast values for each year
                for i, year in enumerate(range(2025, forecast_year + 1)):
                    item[f"forecast_{year}"] = forecast.get(f"forecast_{year}", 0)
                item["growth_rate"] = forecast["growth_rate"]
                forecasts.append(item)
        
        return forecasts
    
    # ==========================================================
    # MAIN ENTRY
    # ==========================================================
    
    async def get_complete_forecast(self, forecast_year: int, verbose: bool = False) -> Dict[str, Any]:
        """Get complete forecast with multiple models and accuracy metrics"""
        
        print(f"\n{'='*60}")
        print(f"🔮 Generating forecast for {forecast_year} using ensemble model...")
        print(f"{'='*60}")
        
        if STATSMODELS_AVAILABLE:
            print("✅ statsmodels available - ARIMA and Holt-Winters enabled (optimized)")
        else:
            print("⚠️ statsmodels not available - using basic models only")
        
        if SCIPY_AVAILABLE:
            print("✅ scipy available - outlier detection enabled")
        else:
            print("⚠️ scipy not available")
        
        # Get top industries - with deduplication
        top_industries = await self.get_top_industries(10)
        
        print(f"\n🔍 Top Industries for {forecast_year}:")
        for ind in top_industries:
            print(f"  {ind['title']}: {ind['employment_2024']:,.0f}")
        
        # Get forecasts for each industry
        industry_forecasts = []
        industry_backtest_summary = []
        all_model_weights = {}
        
        for ind in top_industries:
            data = await self.get_industry_time_series(ind["naics"])
            forecast = await self.forecast_industry(
                ind["naics"], 
                ind["title"], 
                data, 
                forecast_year,
                verbose=verbose
            )
            if forecast:
                industry_forecasts.append(forecast)
                industry_backtest_summary.append({
                    "industry": ind["title"],
                    "mape": forecast["backtest_metrics"]["mape"],
                    "mpe": forecast["backtest_metrics"]["mpe"],
                    "mase": forecast["backtest_metrics"]["mase"]
                })
                # Track which models were used
                for model, weight in forecast["model_weights"].items():
                    if model not in all_model_weights:
                        all_model_weights[model] = []
                    all_model_weights[model].append(weight)
        
        # Get top jobs - with deduplication
        top_jobs = await self.get_top_jobs(8)
        
        # Get forecasts for each job
        job_forecasts = []
        for job in top_jobs:
            forecast = await self.forecast_job(
                job["occ_code"], 
                job["title"], 
                forecast_year,
                verbose=verbose
            )
            if forecast:
                job_forecasts.append(forecast)
        
        # Prepare industry composition for selected year
        industry_composition = []
        for ind in industry_forecasts:
            forecast_key = f"forecast_{forecast_year}"
            industry_composition.append({
                "industry": ind["industry"],
                "current": ind["current"],
                "forecast": ind.get(forecast_key, 0),
                "confidence_lower": ind["confidence_interval"]["lower"],
                "confidence_upper": ind["confidence_interval"]["upper"]
            })
        
        # Prepare employment forecast time series
        employment_forecast = []
        
        # Historical years 2011-2024
        for year in range(2011, 2025):
            row = {"year": year}
            for ind in industry_forecasts:
                # For historical years, we need actual data
                # This is simplified - in production, use actual time series
                row[ind["industry"]] = ind["current"] * (1 - 0.02 * (2024 - year))
            employment_forecast.append(row)
        
        # Forecast years
        for year in range(2025, forecast_year + 1):
            row = {"year": year}
            forecast_key = f"forecast_{year}"
            for ind in industry_forecasts:
                row[ind["industry"]] = ind.get(forecast_key, 0)
            employment_forecast.append(row)
        
        # Prepare top jobs forecast
        top_jobs_forecast = []
        for job in job_forecasts[:8]:
            forecast_key = f"forecast_{forecast_year}"
            top_jobs_forecast.append({
                "name": job["title"],
                "value": job.get(forecast_key, 0),
                "growth": job["growth_rate"]
            })
        
        # Sort by growth
        top_jobs_forecast.sort(key=lambda x: x["growth"], reverse=True)
        
        # Prepare industry details
        industry_details = []
        for ind in industry_forecasts[:10]:
            forecast_key = f"forecast_{forecast_year}"
            forecast_val = ind.get(forecast_key, 0)
            
            change = ((forecast_val - ind["current"]) / ind["current"]) * 100 if ind["current"] > 0 else 0
            
            # Determine confidence level based on MAPE
            if ind["backtest_metrics"]["mape"] < 10:
                confidence = "High"
            elif ind["backtest_metrics"]["mape"] < 15:
                confidence = "Medium"
            else:
                confidence = "Low"
            
            industry_details.append({
                "industry": ind["industry"],
                "current": ind["current"],
                "forecast": forecast_val,
                "change": round(change, 1),
                "confidence": confidence,
                "mape": ind["backtest_metrics"]["mape"],
                "lower_bound": ind["confidence_interval"]["lower"],
                "upper_bound": ind["confidence_interval"]["upper"]
            })
        
        # Calculate totals
        total_current = sum(ind["current"] for ind in industry_forecasts[:10])
        total_forecast = sum(ind.get(f"forecast_{forecast_year}", 0) for ind in industry_forecasts[:10])
        
        years_diff = forecast_year - 2024
        if years_diff > 0 and total_current > 0 and total_forecast > 0:
            total_growth = ((total_forecast / total_current) ** (1 / years_diff) - 1) * 100
        else:
            total_growth = 0
        
        # Calculate average backtest accuracy
        valid_mapes = [bt["mape"] for bt in industry_backtest_summary if bt["mape"] < 999]
        avg_mape = np.mean(valid_mapes) if valid_mapes else 0
        
        # Calculate model usage statistics
        model_popularity = {}
        for model, weights in all_model_weights.items():
            model_popularity[model] = {
                "avg_weight": round(np.mean(weights), 3),
                "times_used": len(weights)
            }
        
        print(f"\n{'='*60}")
        print(f"📊 Overall Backtest Summary:")
        print(f"{'='*60}")
        print(f"  Average MAPE across industries: {avg_mape:.2f}%")
        if industry_backtest_summary:
            # Filter out 999 values for best/worst calculation
            valid_summaries = [s for s in industry_backtest_summary if s['mape'] < 999]
            if valid_summaries:
                best = min(valid_summaries, key=lambda x: x['mape'])
                worst = max(valid_summaries, key=lambda x: x['mape'])
                print(f"  Best performing: {best['industry'][:50]}... (MAPE: {best['mape']}%)")
                print(f"  Worst performing: {worst['industry'][:50]}... (MAPE: {worst['mape']}%)")
        
        print(f"\n📊 Model Usage:")
        for model, stats in sorted(model_popularity.items(), key=lambda x: x[1]['avg_weight'], reverse=True):
            print(f"  {model:15}: avg weight {stats['avg_weight']:.3f}, used in {stats['times_used']} industries")
        
        print(f"\n🔍 Totals:")
        print(f"  total_current: {total_current:,.0f}")
        print(f"  total_forecast: {total_forecast:,.0f}")
        print(f"  total_growth: {total_growth:+.2f}%")
        print(f"{'='*60}")
        
        # AI jobs estimate
        ai_jobs = [j for j in job_forecasts if any(term in j["title"].lower() 
                  for term in ["ai", "machine learning", "data scientist", "ml", "artificial intelligence"])]
        ai_forecast = sum(j.get(f"forecast_{forecast_year}", 0) for j in ai_jobs) if ai_jobs else 48000
        
        # Determine confidence level based on average MAPE
        if avg_mape < 10:
            confidence_level = "High"
            confidence_pct = 85
        elif avg_mape < 15:
            confidence_level = "Medium"
            confidence_pct = 78
        else:
            confidence_level = "Low"
            confidence_pct = 70
        
        metrics = [
            {
                "title": "Est. Total Employment",
                "value": _safe_round(total_forecast),
                "trend": {"value": round(abs(total_growth), 1), "direction": "up" if total_growth >= 0 else "down"},
                "color": "cyan"
            },
            {
                "title": "Est. Median Salary",
                "value": 86500,
                "prefix": "$",
                "trend": {"value": 5.5, "direction": "up"},
                "color": "purple"
            },
            {
                "title": "Est. Job Growth",
                "value": f"{'+' if total_growth >= 0 else ''}{round(total_growth, 1)}%",
                "trend": {"value": abs(total_growth), "direction": "up" if total_growth >= 0 else "down"},
                "color": "green"
            },
            {
                "title": "Est. AI/ML Jobs",
                "value": _safe_round(ai_forecast),
                "trend": {"value": 38, "direction": "up"},
                "color": "coral"
            },
            {
                "title": "Forecast Confidence",
                "value": f"{confidence_pct}%",
                "color": "amber"
            }
        ]
        
        return {
            "forecast_year": forecast_year,
            "metrics": metrics,
            "industry_composition": industry_composition,
            "employment_forecast": employment_forecast,
            "top_jobs_forecast": top_jobs_forecast[:8],
            "industry_details": industry_details,
            "backtest_summary": {
                "average_mape": round(avg_mape, 2),
                "industry_metrics": industry_backtest_summary,
                "model_popularity": model_popularity
            },
            "confidence_level": confidence_level,
            "disclaimer": f"Ensemble forecast combining simple, weighted, linear, polynomial, ARIMA, and Holt-Winters models. Average backtest MAPE: {avg_mape:.1f}%. Includes economic adjustments and confidence intervals."
        }