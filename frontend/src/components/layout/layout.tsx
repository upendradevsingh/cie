import * as React from "react";
import { cn } from "@/lib/utils";
import { Sidebar, type SidebarUser } from "@/components/layout/sidebar";
import { Header, type HeaderUser } from "@/components/layout/header";

export interface LayoutProps {
  children: React.ReactNode;
  pageTitle: string;
  pageSubtitle?: string;
  activePath?: string;
  user?: SidebarUser & HeaderUser;
  showSearch?: boolean;
  searchPlaceholder?: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  onNavigate?: (href: string) => void;
  onLogout?: () => void;
  headerActions?: React.ReactNode;
  className?: string;
}

function Layout({
  children,
  pageTitle,
  pageSubtitle,
  activePath = "/",
  user,
  showSearch = false,
  searchPlaceholder,
  searchValue,
  onSearchChange,
  onNavigate,
  onLogout,
  headerActions,
  className,
}: LayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200 overflow-hidden">
      {/* Sidebar - fixed left */}
      <Sidebar
        user={user}
        activePath={activePath}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
        onNavigate={onNavigate}
        onLogout={onLogout}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Header */}
        <Header
          title={pageTitle}
          subtitle={pageSubtitle}
          showSearch={showSearch}
          searchPlaceholder={searchPlaceholder}
          searchValue={searchValue}
          onSearchChange={onSearchChange}
          user={user}
          onNavigateProfile={() => onNavigate?.("/profile")}
          onNavigateSettings={() => onNavigate?.("/settings")}
          onLogout={onLogout}
          actions={headerActions}
        />

        {/* Scrollable Content */}
        <main
          className={cn(
            "flex-1 overflow-y-auto p-6",
            className
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}

export { Layout };
