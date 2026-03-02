import * as React from "react";
import { Search, Bell, User, Settings, LogOut } from "lucide-react";
import { cn, getInitials } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export interface HeaderUser {
  name: string;
  email: string;
  avatar_url?: string;
}

export interface HeaderProps {
  title: string;
  subtitle?: string;
  showSearch?: boolean;
  searchPlaceholder?: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  user?: HeaderUser;
  onNavigateProfile?: () => void;
  onNavigateSettings?: () => void;
  onLogout?: () => void;
  className?: string;
  actions?: React.ReactNode;
}

function Header({
  title,
  subtitle,
  showSearch = false,
  searchPlaceholder = "Search...",
  searchValue = "",
  onSearchChange,
  user,
  onNavigateProfile,
  onNavigateSettings,
  onLogout,
  className,
  actions,
}: HeaderProps) {
  return (
    <header
      className={cn(
        "flex h-14 items-center justify-between border-b border-slate-800 bg-slate-950/80 px-6 backdrop-blur-sm",
        className
      )}
    >
      {/* Left: Title */}
      <div className="flex flex-col">
        <h1 className="text-lg font-semibold text-white leading-tight">
          {title}
        </h1>
        {subtitle && (
          <p className="text-xs text-slate-400">{subtitle}</p>
        )}
      </div>

      {/* Right: Search + Actions + User */}
      <div className="flex items-center gap-3">
        {showSearch && (
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <Input
              value={searchValue}
              onChange={(e) => onSearchChange?.(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-64 pl-9 h-8 bg-slate-900/50 border-slate-800"
            />
          </div>
        )}

        {actions}

        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-slate-400 hover:text-white"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
        </Button>

        {user && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="relative h-8 w-8 rounded-full"
              >
                <Avatar className="h-8 w-8">
                  {user.avatar_url && (
                    <AvatarImage src={user.avatar_url} alt={user.name} />
                  )}
                  <AvatarFallback className="text-xs">
                    {getInitials(user.name)}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none text-white">
                    {user.name}
                  </p>
                  <p className="text-xs leading-none text-slate-400">
                    {user.email}
                  </p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onNavigateProfile}>
                <User className="mr-2 h-4 w-4" />
                <span>Profile</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onNavigateSettings}>
                <Settings className="mr-2 h-4 w-4" />
                <span>Settings</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={onLogout}
                className="text-red-400 focus:text-red-400"
              >
                <LogOut className="mr-2 h-4 w-4" />
                <span>Log out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </header>
  );
}

export { Header };
