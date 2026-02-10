import { redirect } from "next/navigation";

/** Inventory is now per-product on the product edit page. Redirect old links. */
export default function InventoryPage() {
  redirect("/products");
}
