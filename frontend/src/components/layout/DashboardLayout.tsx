import { TopNavigation } from './TopNavigation';
import { MarketTicker } from './MarketTicker';
import { Footer } from './Footer';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <TopNavigation />
      <MarketTicker />
      <main className="container mx-auto px-4 py-6 page-enter flex-1">
        {children}
      </main>
      <Footer />
    </div>
  );
}
