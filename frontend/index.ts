import { createApp } from "vue";
import App from "./App.vue";

import { createVuetify } from "vuetify";
import * as directives from "vuetify/lib/directives/index.mjs";
import "vuetify/dist/vuetify.css";
import "./styles/tokens.css";
import { defaultThemeName, icons, themes } from "./theme";

if (__APP_NAME__) {
  console.log(
    `Starting ${__APP_NAME__} v${__APP_VERSION__} (${__APP_GIT_SHA__}${__APP_GIT_DIRTY__ ? "+dirty" : ""})...`,
  );
}

const vuetify = createVuetify({
  directives,
  icons,
  theme: {
    defaultTheme: defaultThemeName(),
    themes,
  },
});

const app = createApp(App);
app.use(vuetify);
app.mount("body");
