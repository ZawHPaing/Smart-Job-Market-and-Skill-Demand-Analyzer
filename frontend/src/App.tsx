import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { YearProvider } from "@/components/layout";
import Home from "./pages/Home";
import Industries from "./pages/Industries";
import IndustryDetail from "./pages/IndustryDetail";
import Jobs from "./pages/Jobs";
import JobDetail from "./pages/JobDetail";
import SkillDetail from "./pages/SkillDetail";
import SalaryEmployment from "./pages/SalaryEmployment";
import TrendsForecasts from "./pages/TrendsForecasts";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <YearProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/industries" element={<Industries />} />
            <Route path="/industries/:id" element={<IndustryDetail />} />
            <Route path="/jobs" element={<Jobs />} />
            <Route path="/jobs/:id" element={<JobDetail />} />
            <Route path="/skills/:id" element={<SkillDetail />} />
            <Route path="/salary-employment" element={<SalaryEmployment />} />
            <Route path="/trends" element={<TrendsForecasts />} />
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </YearProvider>
  </QueryClientProvider>
);

export default App;
