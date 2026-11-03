import Link from "next/link";
import { MessagesSquareIcon, PenSquareIcon } from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-backdrop-filter:bg-background/60">
      <div className="mx-auto flex h-14 w-full max-w-4xl items-center gap-2 px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <MessagesSquareIcon className="size-5" />
          <span>데모 게시판</span>
        </Link>
        <div className="ml-auto flex items-center gap-1">
          <Button asChild size="sm">
            <Link href="/posts/new">
              <PenSquareIcon data-icon="inline-start" />
              글쓰기
            </Link>
          </Button>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
