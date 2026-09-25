import { existsSync, statSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { resolve as pathResolve, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

const extensions = [
  "",
  ".ts",
  ".tsx",
  ".js",
  ".jsx",
  "/index.ts",
  "/index.tsx",
  "/index.js",
];

export async function resolve(specifier, context, defaultResolve) {
  let target = specifier;

  // Next.js ESM package subpath mappings
  if (target === "next/link") {
    return defaultResolve("next/link.js", context);
  }
  if (target === "next/image") {
    return defaultResolve("next/image.js", context);
  }

  // Handle path alias "@/..." -> "<cwd>/..."
  if (target.startsWith("@/")) {
    const cwd = process.cwd();
    target = pathResolve(cwd, target.slice(2));
  }

  // Handle relative/absolute paths
  if (
    target.startsWith(".") ||
    target.startsWith("/") ||
    target.includes(":\\") ||
    target.startsWith("file://")
  ) {
    let basePath;
    if (target.startsWith("file://")) {
      basePath = fileURLToPath(target);
    } else if (target.includes(":\\") || target.startsWith("/")) {
      basePath = target;
    } else {
      const parentDir = context.parentURL
        ? dirname(fileURLToPath(context.parentURL))
        : process.cwd();
      basePath = pathResolve(parentDir, target);
    }

    // If it's an existing directory, try index files
    if (existsSync(basePath)) {
      try {
        if (statSync(basePath).isDirectory()) {
          for (const idx of ["/index.ts", "/index.tsx", "/index.js"]) {
            const idxPath = basePath + idx;
            if (existsSync(idxPath)) {
              return {
                url: pathToFileURL(idxPath).href,
                shortCircuit: true,
              };
            }
          }
        }
      } catch {
        // ignore
      }
    }

    // Try candidates
    for (const ext of extensions) {
      const candidate = basePath + ext;
      if (existsSync(candidate) && !statSync(candidate).isDirectory()) {
        return {
          url: pathToFileURL(candidate).href,
          shortCircuit: true,
        };
      }
    }
  }

  return defaultResolve(target, context);
}

export async function load(url, context, defaultLoad) {
  if (url.endsWith(".tsx") || url.endsWith(".ts")) {
    const filePath = fileURLToPath(url);
    const source = await readFile(filePath, "utf8");
    const result = ts.transpileModule(source, {
      compilerOptions: {
        module: ts.ModuleKind.ESNext,
        target: ts.ScriptTarget.ES2022,
        jsx: ts.JsxEmit.React,
        esModuleInterop: true,
      },
    });
    return {
      format: "module",
      source: result.outputText,
      shortCircuit: true,
    };
  }

  return defaultLoad(url, context);
}
