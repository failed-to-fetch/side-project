import { UserIcon } from "lucide-react"

import { Button } from "../shadcn/components/ui/button"
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from "@/shadcn/components/ui/navigation-menu"

import styles from "./header.module.scss"

export interface NavItem {
  label: string
  href: string
}

export interface HeaderProps {
  productName?: string
  items?: NavItem[]
  activeHref?: string
  onAccountClick?: () => void
}

const defaultItems: NavItem[] = [
  { label: "Repositories", href: "/repositories" },
  { label: "Jobs", href: "/jobs" },
  { label: "Saved", href: "/saved" },
]

export default function Header({
  productName = "[Product]",
  items = defaultItems,
  activeHref = items[0]?.href,
  onAccountClick,
}: HeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <span className={styles.brand}>{productName}</span>
        <NavigationMenu>
          <NavigationMenuList>
            {items.map((item) => (
              <NavigationMenuItem key={item.href}>
                <NavigationMenuLink
                  href={item.href}
                  active={item.href === activeHref}
                  className={styles.navLink}
                >
                  {item.label}
                </NavigationMenuLink>
              </NavigationMenuItem>
            ))}
          </NavigationMenuList>
        </NavigationMenu>
      </div>
      <Button
        variant="ghost"
        size="icon"
        className={styles.account}
        aria-label="Account"
        onClick={onAccountClick}
      >
        <UserIcon />
      </Button>
    </header>
  )
}
