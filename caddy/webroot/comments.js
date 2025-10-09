/* global customElements,HTMLElement */
class BlueskyCommentsSection extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.visibleCount = 50;
    this.thread = null;
    this.hiddenReplies = null;
    this.error = null;
  }

  connectedCallback() {
    const postUri = this.getAttribute("post");
    if (!postUri) {
      this.renderError("Post URI is required");
      return;
    }
    this.loadThread(this.#convertUri(postUri));
  }

  #convertUri(uri) {
    if (uri.startsWith("at://")) {
      return uri;
    }

    if (uri.includes("bsky.app/profile/")) {
      const match = uri.match(/profile\/([\w.]+)\/post\/([\w]+)/);
      if (match) {
        const [, did, postId] = match;
        return `at://${did}/app.bsky.feed.post/${postId}`;
      }
    }

    this.error = "Invalid Bluesky post URL format";
    return null;
  }

  async loadThread(uri) {
    try {
      const thread = await this.fetchThread(uri);
      this.thread = thread;
      if (
        "post" in thread &&
        "threadgate" in thread.post &&
        thread.post.threadgate
      ) {
        this.hiddenReplies = thread.post.threadgate?.record?.hiddenReplies;
      }
      this.render();
    } catch (err) {
      this.renderError("Error loading comments");
    }
  }

  async fetchThread(uri) {
    if (!uri || typeof uri !== "string") {
      throw new Error("Invalid URI: A valid string URI is required.");
    }

    const params = new URLSearchParams({ uri });
    const url = `https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?${params.toString()}`;

    try {
      const response = await fetch(url, {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
        cache: "no-store",
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Fetch Error: ", errorText);
        throw new Error(`Failed to fetch thread: ${response.statusText}`);
      }

      const data = await response.json();

      if (!data.thread || !data.thread.replies) {
        throw new Error("Invalid thread data: Missing expected properties.");
      }

      return data.thread;
    } catch (error) {
      console.error("Error fetching thread:", error.message);
      throw error;
    }
  }

  render() {
    if (!this.thread || !this.thread.replies) {
      this.renderError("No comments found");
      return;
    }

    const sortedReplies = this.#filterSortReplies(this.thread.replies);
    if (!sortedReplies || sortedReplies.length === 0) {
      this.renderError("No comments found");
      return;
    }

    const comments = document.createElement("comments");
    comments.innerHTML = `
      <p class="reply-info">
        <a href="https://bsky.app/profile/${
          this.thread.post?.author?.did
        }/post/${this.thread.post?.uri
      .split("/")
      .pop()}" target="_blank" rel="noopener noreferrer">
        Reply on Bluesky</a>
        to leave a comment.
      </p>
      <div id="comments"></div>
      <button id="show-more">
        Show more comments
      </button>
    `;

    const commentsContainer = comments.querySelector("#comments");
    sortedReplies.slice(0, this.visibleCount).forEach((reply) => {
      commentsContainer.appendChild(this.createCommentElement(reply));
    });

    const showMoreButton = comments.querySelector("#show-more");
    if (this.visibleCount >= sortedReplies.length) {
      showMoreButton.style.display = "none";
    }
    showMoreButton.addEventListener("click", () => {
      this.visibleCount += 5;
      this.render();
    });

    this.shadowRoot.innerHTML = "";
    this.shadowRoot.appendChild(comments);

    if (!this.hasAttribute("no-css")) {
      this.addStyles();
    }
  }

  #filterSortReplies(replies) {
    // Filter out blocked/not found replies
    // and replies that only contain 📌
    const filteredReplies = replies.filter((reply) => {
      if (this.hiddenReplies && this.hiddenReplies.includes(reply.post.uri)) {
        return false;
      }
      if ("blocked" in reply && reply.blocked) {
        return false;
      }
      if ("notFound" in reply && reply.notFound) {
        return false;
      }

      const text = reply.post.record?.text || "";
      return text.trim() !== "📌";
    });

    if (!filteredReplies) {
      return [];
    }

    const sortedReplies = filteredReplies.sort(
      (a, b) => (b.post.likeCount ?? 0) - (a.post.likeCount ?? 0)
    );

    return sortedReplies;
  }

  escapeHTML(htmlString) {
    return htmlString
      .replace(/&/g, "&amp;") // Escape &
      .replace(/</g, "&lt;") // Escape <
      .replace(/>/g, "&gt;") // Escape >
      .replace(/"/g, "&quot;") // Escape "
      .replace(/'/g, "&#039;"); // Escape '
  }

  createCommentElement(reply) {
    const comment = document.createElement("div");
    comment.classList.add("comment");

    const author = reply.post.author;
    const text = reply.post.record?.text || "";
    const postId = reply.post.uri.split("/").pop();

    comment.innerHTML = `
      <div class="author">
        <a href="https://bsky.app/profile/${
          author.did
        }/post/${postId}" target="_blank" rel="noopener noreferrer">
          ${author.avatar ? `<img width="22px" src="${author.avatar}" />` : ""}
          ${author.displayName ?? author.handle} @${author.handle}
        </a>
        <p class="comment-text">${this.escapeHTML(text)}</p>
      </div>
    `;

    if (reply.replies && reply.replies.length > 0) {
      const repliesContainer = document.createElement("div");
      repliesContainer.classList.add("replies-container");

      this.#filterSortReplies(reply.replies).forEach((childReply) => {
        repliesContainer.appendChild(this.createCommentElement(childReply));
      });

      comment.appendChild(repliesContainer);
    }

    return comment;
  }

  renderError(message) {
    this.shadowRoot.innerHTML = `<p class="error">${message}</p>`;
  }

  addStyles() {
    const style = document.createElement("style");
    style.textContent = `
        a {
          color: #4eaaff;
          text-decoration: none;
          word-break: break-all;
        }
        a:hover {
          color: #82cfff;
          text-decoration: underline;
        }
        .author {
          a {
            img {
            margin-right: 0.4em;
            border-radius: 100%;
            vertical-align: middle;
            }
          }
        }
    `;
    this.shadowRoot.appendChild(style);
  }
}

customElements.define("bluesky-comments-section", BlueskyCommentsSection);
