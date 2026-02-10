import { redirect } from "next/navigation";

/** Discovery tab removed; push features live under Products. Redirect old links. */
export default function DiscoveryPage() {
  redirect("/products");
}
