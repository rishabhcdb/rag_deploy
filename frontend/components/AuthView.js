import { supabaseClient } from "../supabase.js";

export default {
  name: "AuthView",
  template: `
    <main class="auth-page">
      <section class="auth-card">
        
        <!-- LEFT: Image Panel -->
        <div class="auth-image">
          <!-- Background image set via CSS -->
        </div>

        <!-- RIGHT: Form Panel -->
        <div class="auth-form">
          <div class="form-wrapper">
            
            <h1>{{ isLogin ? "Sign in" : "Create account" }}</h1>
            <p class="subtitle">
              {{ isLogin 
                ? "Welcome back! Please sign in to continue" 
                : "Create your account to get started" }}
            </p>

            <!-- Google Auth -->
            <button class="google-btn" @click.prevent="googleAuth">
              <span class="icon-slot"></span>
              <span>{{ isLogin ? "Sign in with Google" : "Sign up with Google" }}</span>
            </button>

            <div class="divider">
              <span></span>
              <p>or sign in with email</p>
              <span></span>
            </div>

            <!-- Email -->
            <div class="field">
              <span class="icon-slot"></span>
              <input
                type="email"
                placeholder="Email id"
                v-model="email"
              />
            </div>

            <!-- Password -->
            <div class="field">
              <span class="icon-slot"></span>
              <input
                type="password"
                placeholder="Password"
                v-model="password"
              />
            </div>

            <!-- Extras -->
            <div class="form-row" v-if="isLogin">
              <label class="checkbox">
                <input type="checkbox" v-model="remember" />
                <span>Remember me</span>
              </label>
              <a href="#" class="link">Forgot password?</a>
            </div>

            <!-- Primary CTA -->
            <button class="primary-btn" @click.prevent="submit">
              {{ isLogin ? "Login" : "Sign up" }}
            </button>

            <!-- Switch -->
            <p class="switch">
              {{ isLogin ? "Don't have an account?" : "Already have an account?" }}
              <a href="#" @click.prevent="toggle">
                {{ isLogin ? "Sign up" : "Sign in" }}
              </a>
            </p>

          </div>
        </div>

      </section>
    </main>
  `,
  data() {
    return {
      isLogin: true,
      email: "",
      password: "",
      remember: false
    };
  },
  methods: {
    toggle() {
        this.isLogin = !this.isLogin;
    },

    async googleAuth() {
        const { error } = await supabaseClient.auth.signInWithOAuth({
        provider: "google",
        options: {
            redirectTo: window.location.origin + "/chat"
        }
        });

        if (error) {
        alert(error.message);
        }
    },

    async submit() {
        if (!this.email || !this.password) {
        alert("Please fill all fields");
        return;
        }

        let result;

        if (this.isLogin) {
        // LOGIN
        result = await supabaseClient.auth.signInWithPassword({
            email: this.email,
            password: this.password
        });
        } else {
        // SIGN UP
        result = await supabaseClient.auth.signUp({
            email: this.email,
            password: this.password
        });
        }

        if (result.error) {
        alert(result.error.message);
        return;
        }
        const { data: sessionData } = await supabaseClient.auth.getSession();

        if (!sessionData.session) {
            alert("Please verify your email before logging in.");
            return;
        }

        // Success → go to chat
        this.$router.push("/chat");
    }
    }
};
