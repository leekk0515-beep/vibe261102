import Link from "next/link";
import { Suspense } from "react";
import { MessageSquareIcon, SearchIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { listPosts, type SearchField } from "@/lib/db";
import { formatDate } from "@/lib/format";

const FIELDS: { value: SearchField; label: string }[] = [
  { value: "all", label: "제목+내용" },
  { value: "title", label: "제목" },
  { value: "content", label: "내용" },
];

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function first(v: string | string[] | undefined) {
  return Array.isArray(v) ? v[0] : v;
}

function parseParams(sp: Awaited<SearchParams>) {
  const q = first(sp.q) ?? "";
  const rawField = first(sp.field);
  const field: SearchField = FIELDS.some((f) => f.value === rawField)
    ? (rawField as SearchField)
    : "all";
  const page = Number.parseInt(first(sp.page) ?? "1", 10);
  return { q, field, page: Number.isFinite(page) && page > 0 ? page : 1 };
}

export default function Home({ searchParams }: { searchParams: SearchParams }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">게시글 목록</CardTitle>
        <CardDescription>자유롭게 글을 남기고 이야기를 나눠 보세요.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <Suspense fallback={<ListSkeleton />}>
          <PostList searchParams={searchParams} />
        </Suspense>
      </CardContent>
    </Card>
  );
}

async function PostList({ searchParams }: { searchParams: SearchParams }) {
  const { q, field, page } = parseParams(await searchParams);
  const result = await listPosts({ query: q, field, page });

  const hrefFor = (p: number) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (q && field !== "all") params.set("field", field);
    if (p > 1) params.set("page", String(p));
    const s = params.toString();
    return s ? `/?${s}` : "/";
  };

  return (
    <>
      <SearchForm q={q} field={field} />

      <p className="text-sm text-muted-foreground">
        {q ? (
          <>
            <span className="font-medium text-foreground">‘{q}’</span> 검색 결과{" "}
            {result.total}건
          </>
        ) : (
          <>전체 {result.total}건</>
        )}
      </p>

      {result.items.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed py-12 text-center text-sm text-muted-foreground">
          {q ? "검색 결과가 없습니다." : "아직 게시글이 없습니다. 첫 글을 작성해 보세요!"}
          {q ? (
            <Button variant="outline" size="sm" asChild>
              <Link href="/">전체 목록 보기</Link>
            </Button>
          ) : (
            <Button size="sm" asChild>
              <Link href="/posts/new">글쓰기</Link>
            </Button>
          )}
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="hidden w-16 text-center sm:table-cell">번호</TableHead>
              <TableHead>제목</TableHead>
              <TableHead className="hidden w-28 md:table-cell">작성자</TableHead>
              <TableHead className="hidden w-28 text-right sm:table-cell">작성일</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {result.items.map((post, i) => {
              const no = result.total - (result.page - 1) * result.pageSize - i;
              return (
                <TableRow key={post.id}>
                  <TableCell className="hidden text-center text-muted-foreground sm:table-cell">
                    {no}
                  </TableCell>
                  <TableCell className="max-w-0 whitespace-normal">
                    <Link
                      href={`/posts/${post.id}`}
                      className="flex items-center gap-2 font-medium hover:underline"
                    >
                      <span className="truncate">{post.title}</span>
                      {post.commentCount > 0 && (
                        <Badge variant="secondary" className="shrink-0 gap-1">
                          <MessageSquareIcon />
                          {post.commentCount}
                        </Badge>
                      )}
                    </Link>
                    <p className="mt-1 text-xs text-muted-foreground md:hidden">
                      {post.author}
                      <span className="sm:hidden"> · {formatDate(post.createdAt)}</span>
                    </p>
                  </TableCell>
                  <TableCell className="hidden truncate md:table-cell">{post.author}</TableCell>
                  <TableCell className="hidden text-right text-muted-foreground sm:table-cell">
                    {formatDate(post.createdAt)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}

      {result.totalPages > 1 && (
        <PageNav page={result.page} totalPages={result.totalPages} hrefFor={hrefFor} />
      )}
    </>
  );
}

function SearchForm({ q, field }: { q: string; field: SearchField }) {
  return (
    <form action="/" className="flex flex-col gap-2 sm:flex-row" role="search">
      <select
        name="field"
        defaultValue={field}
        aria-label="검색 범위"
        className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 sm:w-32 dark:bg-input/30 [&>option]:bg-popover [&>option]:text-popover-foreground"
      >
        {FIELDS.map((f) => (
          <option key={f.value} value={f.value}>
            {f.label}
          </option>
        ))}
      </select>
      <div className="flex flex-1 gap-2">
        <Input
          type="search"
          name="q"
          defaultValue={q}
          placeholder="검색어를 입력하세요"
          aria-label="검색어"
        />
        <Button type="submit" variant="secondary">
          <SearchIcon data-icon="inline-start" />
          검색
        </Button>
      </div>
    </form>
  );
}

function pageWindow(page: number, total: number): (number | "…")[] {
  const pages = new Set([1, total, page - 1, page, page + 1]);
  const sorted = [...pages].filter((p) => p >= 1 && p <= total).sort((a, b) => a - b);
  const out: (number | "…")[] = [];
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) out.push("…");
    out.push(p);
  });
  return out;
}

function PageNav({
  page,
  totalPages,
  hrefFor,
}: {
  page: number;
  totalPages: number;
  hrefFor: (p: number) => string;
}) {
  return (
    <Pagination>
      <PaginationContent>
        <PaginationItem>
          <PaginationPrevious
            text="이전"
            aria-label="이전 페이지"
            href={hrefFor(Math.max(1, page - 1))}
            aria-disabled={page === 1}
            className={page === 1 ? "pointer-events-none opacity-50" : undefined}
          />
        </PaginationItem>
        {pageWindow(page, totalPages).map((p, i) =>
          p === "…" ? (
            <PaginationItem key={`e${i}`}>
              <PaginationEllipsis />
            </PaginationItem>
          ) : (
            <PaginationItem key={p}>
              <PaginationLink href={hrefFor(p)} isActive={p === page}>
                {p}
              </PaginationLink>
            </PaginationItem>
          ),
        )}
        <PaginationItem>
          <PaginationNext
            text="다음"
            aria-label="다음 페이지"
            href={hrefFor(Math.min(totalPages, page + 1))}
            aria-disabled={page === totalPages}
            className={page === totalPages ? "pointer-events-none opacity-50" : undefined}
          />
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  );
}

function ListSkeleton() {
  return (
    <div className="grid gap-3" aria-busy="true" aria-label="불러오는 중">
      <div className="h-8 animate-pulse rounded-lg bg-muted" />
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="h-10 animate-pulse rounded-lg bg-muted/60" />
      ))}
    </div>
  );
}
