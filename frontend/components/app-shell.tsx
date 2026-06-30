"use client";

import { usePathname, useRouter } from "next/navigation";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

const NAV = [
  { href: "/", label: "Airline" },
  { href: "/fleet", label: "Fleet" },
  { href: "/compare", label: "Compare Aircraft" },
  { href: "/compare/airlines", label: "Compare Airline" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const activePath = NAV.some((item) => item.href === pathname)
    ? pathname
    : pathname.startsWith("/aircraft")
      ? "/fleet"
      : "/";

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between px-6 py-3">
          <div>
            <h1 className="text-sm font-semibold tracking-tight">
              Flight Benchmarking
            </h1>
            <p className="text-xs text-muted-foreground">
              Features Comparison
            </p>
          </div>
          <Tabs
            value={activePath}
            onValueChange={(value) => value && router.push(value)}
          >
            <TabsList variant="line" className="h-8">
              {NAV.map((item) => (
                <TabsTrigger
                  key={item.href}
                  value={item.href}
                  className="px-3 text-xs"
                >
                  {item.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
      </header>
      <main className="mx-auto max-w-screen-2xl px-6 py-6">{children}</main>
    </div>
  );
}
