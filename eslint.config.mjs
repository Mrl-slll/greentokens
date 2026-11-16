import next from "eslint-config-next";
const config = [...next, { ignores: [".next/**", "node_modules/**", ".venv/**", ".tools/**", "examples/**/.cache/**", "apps/**"] }];
export default config;
