"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import * as db from "@/lib/db";

export type FormState = {
  errors?: Partial<Record<"title" | "content" | "author", string>>;
  message?: string;
  values?: { title?: string; content?: string; author?: string };
  ok?: boolean;
};

const LIMITS = { title: 100, content: 10_000, author: 20, comment: 1_000 };

function text(formData: FormData, key: string) {
  const v = formData.get(key);
  return typeof v === "string" ? v.trim() : "";
}

function validatePost(formData: FormData) {
  const values = {
    title: text(formData, "title"),
    content: text(formData, "content"),
    author: text(formData, "author"),
  };
  const errors: FormState["errors"] = {};
  if (!values.title) errors.title = "제목을 입력해 주세요.";
  else if (values.title.length > LIMITS.title)
    errors.title = `제목은 ${LIMITS.title}자 이하로 입력해 주세요.`;
  if (!values.content) errors.content = "내용을 입력해 주세요.";
  else if (values.content.length > LIMITS.content)
    errors.content = `내용은 ${LIMITS.content.toLocaleString()}자 이하로 입력해 주세요.`;
  if (!values.author) errors.author = "작성자를 입력해 주세요.";
  else if (values.author.length > LIMITS.author)
    errors.author = `작성자는 ${LIMITS.author}자 이하로 입력해 주세요.`;
  return { values, errors, valid: Object.keys(errors).length === 0 };
}

export async function createPostAction(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const { values, errors, valid } = validatePost(formData);
  if (!valid) return { errors, values };

  const post = await db.createPost(values);
  revalidatePath("/");
  redirect(`/posts/${post.id}`);
}

export async function updatePostAction(
  id: string,
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const { values, errors, valid } = validatePost(formData);
  if (!valid) return { errors, values };

  const post = await db.updatePost(id, values);
  if (!post) return { message: "게시글을 찾을 수 없습니다.", values };
  revalidatePath("/");
  revalidatePath(`/posts/${id}`);
  redirect(`/posts/${id}`);
}

export async function deletePostAction(id: string) {
  await db.deletePost(id);
  revalidatePath("/");
  redirect("/");
}

export async function addCommentAction(
  postId: string,
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const author = text(formData, "author");
  const content = text(formData, "content");
  const values = { author, content };
  const errors: FormState["errors"] = {};
  if (!author) errors.author = "작성자를 입력해 주세요.";
  else if (author.length > LIMITS.author)
    errors.author = `작성자는 ${LIMITS.author}자 이하로 입력해 주세요.`;
  if (!content) errors.content = "댓글 내용을 입력해 주세요.";
  else if (content.length > LIMITS.comment)
    errors.content = `댓글은 ${LIMITS.comment.toLocaleString()}자 이하로 입력해 주세요.`;
  if (Object.keys(errors).length) return { errors, values };

  const comment = await db.addComment(postId, values);
  if (!comment) return { message: "게시글을 찾을 수 없습니다.", values };
  revalidatePath(`/posts/${postId}`);
  revalidatePath("/");
  // 작성자 이름은 다음 댓글을 위해 유지합니다.
  return { ok: true, values: { author } };
}

export async function deleteCommentAction(postId: string, commentId: string) {
  await db.deleteComment(commentId);
  revalidatePath(`/posts/${postId}`);
  revalidatePath("/");
}
