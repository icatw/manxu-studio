import { Link as RouterLink, type LinkProps } from "react-router";

type AppLinkProps = Omit<LinkProps, "to"> & { href: string };

export default function Link({ href, ...props }: AppLinkProps) {
  return <RouterLink to={href} {...props} />;
}
