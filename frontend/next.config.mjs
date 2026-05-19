/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config) => {
    // Workaround para Node.js 24+ donde `fs.readlink` lanza EISDIR sobre
    // archivos regulares. Forzamos a webpack a no resolver symlinks.
    config.resolve.symlinks = false;
    return config;
  },
};

export default nextConfig;
