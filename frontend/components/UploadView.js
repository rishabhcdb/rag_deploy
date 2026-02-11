export default {
  template: `
    <div class="container mt-5">
      <h3>Upload PDF</h3>
      <input type="file" @change="handleFile" />
      <button class="btn btn-success mt-2" @click="upload">Upload</button>
    </div>
  `,
  data() {
    return { file: null };
  },
  methods: {
    handleFile(e) {
      this.file = e.target.files[0];
    },
    async upload() {
      const formData = new FormData();
      formData.append("file", this.file);

      await fetch("/api/upload", {
        method: "POST",
        headers: {
          Authorization: "Bearer " + localStorage.getItem("token"),
        },
        body: formData,
      });

      this.$router.push("/chat");
    },
  },
};
