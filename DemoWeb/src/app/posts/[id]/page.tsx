import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ArrowLeftIcon, PencilIcon } from "lucide-react";

import { CommentForm } from "@/components/comment-form";
import { DeleteCommentButton } from "@/components/delete-comment-button";
import { DeletePostButton } from "@/components/delete-post-button";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { getPost } from "@/lib/db";
import { formatDateTime } from "@/lib/format";

export async function generateMetadata({
  params,
}: PageProps<"/posts/[id]">): Promise<Metadata> {
  const { id } = await params;
  const data = await getPost(id);
  return { title: data?.post.title ?? "게시글을 찾을 수 없음" };
}

export default function PostPage({ params }: PageProps<"/posts/[id]">) {
  return (
    <div className="grid gap-6">
      <div>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/">
            <ArrowLeftIcon data-icon="inline-start" />
            목록으로
          </Link>
        </Button>
      </div>
      <Suspense fallback={<DetailSkeleton />}>
        <PostDetail params={params} />
      </Suspense>
    </div>
  );
}

async function PostDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = await getPost(id);
  if (!data) notFound();
  const { post, comments } = data;
  const edited = post.updatedAt !== post.createdAt;

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="text-xl leading-snug break-words sm:text-2xl">
            {post.title}
          </CardTitle>
          <CardDescription className="flex flex-wrap gap-x-3 gap-y-1">
            <span className="font-medium text-foreground">{post.author}</span>
            <span>{formatDateTime(post.createdAt)}</span>
            {edited && <span>(수정됨 {formatDateTime(post.updatedAt)})</span>}
          </CardDescription>
        </CardHeader>
        <Separator />
        <CardContent>
          <div className="min-h-32 text-[0.95rem] leading-7 break-words whitespace-pre-wrap">
            {post.content}
          </div>
        </CardContent>
        <CardFooter className="justify-end gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/posts/${post.id}/edit`}>
              <PencilIcon data-icon="inline-start" />
              수정
            </Link>
          </Button>
          <DeletePostButton id={post.id} />
        </CardFooter>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>댓글 {comments.length}개</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-6">
          {comments.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              첫 댓글을 남겨 보세요.
            </p>
          ) : (
            <ul className="grid gap-4">
              {comments.map((c) => (
                <li key={c.id} className="rounded-lg border p-3">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-medium">{c.author}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatDateTime(c.createdAt)}
                    </span>
                    <span className="ml-auto">
                      <DeleteCommentButton postId={post.id} commentId={c.id} />
                    </span>
                  </div>
                  <p className="mt-1.5 text-sm leading-6 break-words whitespace-pre-wrap">
                    {c.content}
                  </p>
                </li>
              ))}
            </ul>
          )}
          <Separator />
          <CommentForm postId={post.id} />
        </CardContent>
      </Card>
    </>
  );
}

function DetailSkeleton() {
  return (
    <div className="grid gap-4" aria-busy="true" aria-label="불러오는 중">
      <div className="h-8 w-2/3 animate-pulse rounded-lg bg-muted" />
      <div className="h-4 w-1/3 animate-pulse rounded bg-muted/60" />
      <div className="h-48 animate-pulse rounded-lg bg-muted/60" />
    </div>
  );
}
