/// <reference types="vite/client" />

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<object, object, unknown>;
  export default component;
}

declare const __APP_NAME__: string;
declare const __APP_VERSION__: string;
declare const __APP_GIT_SHA__: string;
declare const __APP_GIT_DIRTY__: string;
declare const __CADQUERY_WEB_VIEWER_SMALL_BUILD__: boolean;

declare module "tanmayo7lock?raw" {
  const src: string;
  export default src;
}

declare module "@jamescoyle/vue-icon" {
  import type { DefineComponent } from "vue";
  const SvgIcon: DefineComponent<{ path: string; type?: string }, object, unknown>;
  export default SvgIcon;
}
