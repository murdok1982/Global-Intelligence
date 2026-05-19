import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const publicRoutes = ['/', '/auth'];

export function middleware(request: NextRequest) {
  // 'session_present' is a non-sensitive boolean cookie set on login.
  // The access token itself lives only in JS memory (never in any cookie or
  // localStorage), so the middleware uses this sentinel for route-guarding only.
  const sessionPresent = request.cookies.get('session_present')?.value;
  const { pathname } = request.nextUrl;

  const isPublicRoute = publicRoutes.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );

  if (!sessionPresent && !isPublicRoute) {
    return NextResponse.redirect(new URL('/auth', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
