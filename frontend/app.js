import UploadView from "./components/UploadView.js";
import ChatView from "./components/ChatView.js";
import AuthView from "./components/AuthView.js";
import { supabaseClient } from "./supabase.js";

const routes = [
  { path: "/", component: AuthView },
  { path: "/upload", component: UploadView },
  { path: "/chat", component: ChatView },
];

const router = VueRouter.createRouter({
  history: VueRouter.createWebHistory(),
  routes,
});

router.beforeEach(async (to, from, next) => {
  const publicRoutes = ["/"];

  const { data } = await supabaseClient.auth.getSession();
  const session = data?.session;

  if (!publicRoutes.includes(to.path) && !session) {
    return next("/");
  }

  next();
});

supabaseClient.auth.onAuthStateChange((event, session) => {
  if (session) {
    localStorage.setItem("token", session.access_token);
  } else {
    localStorage.removeItem("token");
  }
});

const app = Vue.createApp({});
app.use(router);
app.mount("#app");
