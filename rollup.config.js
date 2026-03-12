import commonjs from "@rollup/plugin-commonjs";
import json from "@rollup/plugin-json";
import { nodeResolve } from "@rollup/plugin-node-resolve";
import replace from "@rollup/plugin-replace";
import typescript from "@rollup/plugin-typescript";
import importCss from "rollup-plugin-import-css";

import { defineConfig } from "rollup";

export default defineConfig({
  input: "./src/index.tsx",
  plugins: [
    commonjs(),
    nodeResolve(),
    typescript(),
    json(),
    replace({
      preventAssignment: false,
      "process.env.NODE_ENV": JSON.stringify("production"),
    }),
    importCss(),
  ],
  context: "window",
  external: ["react", "react-dom", "react-dom/client"],
  output: {
    file: "dist/index.js",
    globals: {
      react: "SP_REACT",
      "react-dom": "SP_REACTDOM",
      "react-dom/client": "SP_REACTDOM",
    },
    format: "iife",
    exports: "default",
  },
});
