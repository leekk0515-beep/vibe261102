import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { updatePostAction } from "@/app/actions";
import { PostForm } from "@/components/post-form";
import { getPost } from "@/lib/db";

export const metadata: Metadata = { title: "글 수정" };

export default function EditPostPage({ params }: PageProps<"/posts/[id]/edit">) {
  return (
    <Suspense
      fallback={<div className="h-96 animate-pulse rounded-xl bg-muted/60" />}
    >
      <EditForm params={params} />
    </Suspense>
  );
}

async function EditForm({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = await getPost(id);
  if (!data) notFound();
  const { title, content, author } = data.post;

  return (
    <PostForm
      heading="글 수정"
      submitLabel="수정 완료"
      cancelHref={`/posts/${id}`}
      action={updatePostAction.bind(null, id)}
      defaultValues={{ title, content, author }}
    />
  );
}
