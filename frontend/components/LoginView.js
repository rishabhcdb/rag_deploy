export default {
  template: `
    <div class="container mt-5">
      <h3>Login</h3>
      <button class="btn btn-primary" @click="login">Mock Login</button>
    </div>
  `,
  methods: {
    login() {
      // TEMP: replace with Supabase later
      localStorage.setItem("token", "dev-token");
      this.$router.push("/upload");
    },
  },
};
