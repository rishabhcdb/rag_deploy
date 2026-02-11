import { supabaseClient } from "../supabase.js";
export default {
  name: "ChatView",

  template: `
    <main class="chat-page">

      <!-- Sidebar toggle (mobile) -->
      <button class="sidebar-toggle" @click="collapsed = !collapsed">
        ☰
      </button>
      
    
      <!-- Sidebar -->
      <aside class="sidebar" :class="{ collapsed }">
        <h2 style="margin-left: 35px;">Document</h2>
        <button class="logout-btn" @click="logout">Logout</button>

        <div class="doc-card">
          <p class="doc-name">
            {{ docName || "No document uploaded" }}
          </p>

          <p class="doc-meta">
            Status:
            <span v-if="docStatus === 'processing'">Processing…</span>
            <span v-else-if="docStatus === 'indexed'">Indexed</span>
            <span v-else>—</span>
          </p>

          <p class="doc-meta">
            Questions asked: {{ questionCount }} / {{ maxQuestions }}
          </p>
        </div>
      </aside>

      <!-- Chat Area -->
      <section class="chat-area">

        <!-- Messages -->
        <div class="messages">
          <div
            v-for="(msg, i) in messages"
            :key="i"
            :class="['message', msg.role]"
          >
            <div class="message-content">
              <p
                v-for="(line, j) in msg.content.split('\\n')"
                :key="j"
              >
                {{ line }}
              </p>
            </div>
          </div>

          <!-- Loading indicator for assistant -->
          <div v-if="isAsking" class="message assistant">
            <div class="message-content">
              <p>Thinking…</p>
            </div>
          </div>
        </div>

        <!-- Input -->
        <form class="chat-input" @submit.prevent="send">

          <!-- Upload -->
          <label
            class="upload-btn"
            :class="{ disabled: isUploading }"
            title="Upload PDF"
          >
            +
            <input
              type="file"
              accept="application/pdf"
              hidden
              :disabled="isUploading"
              @change="handleUpload"
            />
          </label>

          <!-- Question input -->
          <input
            type="text"
            placeholder="Ask a question about this document…"
            v-model="input"
            :disabled="docStatus !== 'indexed' || isAsking"
          />

          <button
            type="submit"
            :disabled="docStatus !== 'indexed' || isAsking"
          >
            Send
          </button>
        </form>

      </section>
    </main>
  `,

  data() {
    return {
      // UI
      collapsed: false,
      input: "",

      // document state
      docName: null,
      docStatus: "idle", // idle | processing | indexed
      questionCount: 0,
      maxQuestions: 10,

      // async flags
      isUploading: false,
      isAsking: false,

      // chat
      messages: []
    };
  },

  methods: {
    /* -------------------------
       PDF upload + ingestion
    ------------------------- */
    async handleUpload(e) {
      const file = e.target.files[0];
      if (!file) return;

      this.docName = file.name;
      this.docStatus = "processing";
      this.isUploading = true;
      this.messages = [];
      this.questionCount = 0;

      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch("/api/upload", {
          method: "POST",
          headers: {
            Authorization: "Bearer " + localStorage.getItem("token")
          },
          body: formData
        });

        if (!res.ok) {
          throw new Error("Upload failed");
        }

        this.docStatus = "indexed";
      } catch (err) {
        console.error(err);
        alert("Failed to process document.");
        this.docStatus = "idle";
        this.docName = null;
        }finally {    
            this.isUploading = false;
            e.target.value = ""; // reset file input
        }
    },
    async logout() {
        await supabaseClient.auth.signOut();

        // Clear anything app-specific if needed
        localStorage.removeItem("token");

        // Redirect to login
        this.$router.push("/");
    },

    /* -------------------------
       Ask question
    ------------------------- */
    async send() {
      if (!this.input.trim()) return;

      if (this.questionCount >= this.maxQuestions) {
        alert("Question limit reached for this document.");
        return;
      }

      const question = this.input;

      // push user message
      this.messages.push({
        role: "user",
        content: question
      });

      this.input = "";
      this.isAsking = true;
      this.questionCount++;

      try {
        const res = await fetch("/api/ask", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer " + localStorage.getItem("token")
          },
          body: JSON.stringify({ question })
        });

        if (res.status === 429) {
          this.messages.push({
            role: "assistant",
            content: "You’ve reached your question limit for today."
          });
          this.isAsking = false;
          return;
        }

        if (!res.ok) {
          throw new Error("Ask failed");
        }

        const data = await res.json();

        this.messages.push({
          role: "assistant",
          content: data.answer
        });
      } catch (err) {
        this.messages.push({
          role: "assistant",
          content: "Something went wrong. Please try again."
        });
      } finally {
        this.isAsking = false;
      }
    },
    async fetchLimits() {
      const res = await fetch("/api/limits", {
        headers: {
          Authorization: "Bearer " + localStorage.getItem("token")
        }
      });

      if (!res.ok) return;

      const data = await res.json();
      this.questionCount = data.questions_used;
      this.maxQuestions = data.questions_limit;
    }

  },

  mounted() {
  if (window.location.hash.includes("access_token")) {
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  this.fetchLimits();
  }

};
