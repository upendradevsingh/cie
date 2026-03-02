import * as React from "react";
import {
  LayoutDashboard,
  Phone,
  BarChart3,
  Trophy,
  FileText,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn, getInitials } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Separator } from "@/components/ui/separator";

export interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const defaultNavItems: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Calls", href: "/calls", icon: Phone },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "Leaderboard", href: "/leaderboard", icon: Trophy },
  { label: "Reports", href: "/reports", icon: FileText },
  { label: "Settings", href: "/settings", icon: Settings },
];

export interface SidebarUser {
  name: string;
  email: string;
  avatar_url?: string;
}

export interface SidebarProps {
  user?: SidebarUser;
  activePath?: string;
  navItems?: NavItem[];
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  onNavigate?: (href: string) => void;
  onLogout?: () => void;
}

function Sidebar({
  user,
  activePath = "/",
  navItems = defaultNavItems,
  collapsed = false,
  onToggleCollapse,
  onNavigate,
  onLogout,
}: SidebarProps) {
  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "flex h-screen flex-col border-r border-slate-800 bg-slate-950 transition-all duration-300",
          collapsed ? "w-16" : "w-64"
        )}
      >
        {/* Logo */}
        <div className="flex h-14 items-center gap-2 border-b border-slate-800 px-4">
          <span className="text-xl text-teal-400 shrink-0">&#9678;</span>
          {!collapsed && (
            <span className="text-lg font-bold text-white tracking-tight">
              SalesLens
            </span>
          )}
          <Button
            variant="ghost"
            size="icon"
            className={cn(
              "ml-auto h-7 w-7 shrink-0 text-slate-400 hover:text-white",
              collapsed && "ml-0"
            )}
            onClick={onToggleCollapse}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-2 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = activePath === item.href;
            const Icon = item.icon;

            const linkContent = (
              <button
                key={item.href}
                onClick={() => onNavigate?.(item.href)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-[#1e3a5f] text-white"
                    : "text-slate-400 hover:bg-slate-800/50 hover:text-white"
                )}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </button>
            );

            if (collapsed) {
              return (
                <Tooltip key={item.href}>
                  <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                  <TooltipContent side="right">{item.label}</TooltipContent>
                </Tooltip>
              );
            }

            return linkContent;
          })}
        </nav>

        <Separator />

        {/* User Info */}
        {user && (
          <div className="p-3">
            <div
              className={cn(
                "flex items-center gap-3",
                collapsed && "justify-center"
              )}
            >
              <Avatar className="h-8 w-8 shrink-0">
                {user.avatar_url && <AvatarImage src={user.avatar_url} />}
                <AvatarFallback className="text-xs">
                  {getInitials(user.name)}
                </AvatarFallback>
              </Avatar>
              {!collapsed && (
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">
                    {user.name}
                  </p>
                  <p className="text-xs text-slate-500 truncate">
                    {user.email}
                  </p>
                </div>
              )}
              {!collapsed && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 shrink-0 text-slate-400 hover:text-red-400"
                      onClick={onLogout}
                      aria-label="Log out"
                    >
                      <LogOut className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">Log out</TooltipContent>
                </Tooltip>
              )}
            </div>
            {collapsed && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="mt-2 w-full h-7 text-slate-400 hover:text-red-400"
                    onClick={onLogout}
                    aria-label="Log out"
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">Log out</TooltipContent>
              </Tooltip>
            )}
          </div>
        )}
      </aside>
    </TooltipProvider>
  );
}

export { Sidebar, defaultNavItems };
