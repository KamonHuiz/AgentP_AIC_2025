// script.js
document.addEventListener("DOMContentLoaded", () => {
  // --- Lấy element ---
  const searchButton = document.getElementById("search-button");
  const queryInput = document.getElementById("query-input");
  const colorInput = document.getElementById("color-input");
  const ocrInput = document.getElementById("ocr-input");
  const topkInput = document.getElementById("topk-input");
  const gallery = document.getElementById("gallery");
  const viewModeToggle = document.getElementById("view-mode-toggle");
  let videoData = {};

  // Load JSON chứa thông tin video
  fetch("final_videos.json")
    .then((res) => {
      if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
      return res.json();
    })
    .then((data) => {
      videoData = data;
      console.log("✅ Đã load final_videos.json:", videoData);
    })
    .catch((err) => console.error("❌ Lỗi load JSON:", err));

  // Bắt sự kiện cho nút mở YouTube
  document.getElementById("open-youtube-btn").addEventListener("click", () => {
    const videoId = document.getElementById("info-videoid").innerText.trim();
    const frameIndex = parseInt(
      document.getElementById("info-frame").innerText.trim()
    );

    if (videoData && videoData[videoId]) {
      const url = videoData[videoId].watch_url;
      const fps = videoData[videoId].fps;
      const seconds = Math.floor(frameIndex / fps);
      const youtubeUrl = `${url}&t=${seconds}s`;
      window.open(youtubeUrl, "_blank");
    } else {
      alert(`Không tìm thấy video [${videoId}] trong JSON!`);
    }
  });

  // --- Biến trạng thái ---
  let fullData = null;
  let currentViewMode = "frame"; // mặc định xem theo frame

  // --- Map ánh xạ ---
  const pathToVideoIdMap = new Map();
  const videoIdToAllFramesMap = new Map();

  // --- Hằng số host ---
  const HOST = "http://127.0.0.1:5000";
  const addHost = (p) => (p ? (p.startsWith("http") ? p : `${HOST}${p}`) : "");
  const normalizePathFromSrc = (src) => {
    try {
      return new URL(src, HOST).pathname;
    } catch {
      return src;
    }
  };

  // --- Hàm gọi API ---
  async function performSearch() {
    const query = queryInput.value.trim();
    const k = topkInput.value;
    const colors = colorInput.value.trim();
    const ocr = ocrInput.value.trim();
    const modeSelect = document.getElementById("model-select");
    const mode = modeSelect.value || "apple";
    if (!query) {
      alert("Please enter a search query.");
      return;
    }

    gallery.innerHTML = '<p class="placeholder">Loading...</p>';

    let apiUrl = `${HOST}/search?query=${encodeURIComponent(
      query
    )}&k=${k}&mode=${mode}`;
    if (colors) apiUrl += `&colors=${encodeURIComponent(colors)}`;
    if (ocr) apiUrl += `&ocr=${encodeURIComponent(ocr)}`;

    try {
      const response = await fetch(apiUrl);
      if (!response.ok)
        throw new Error(`HTTP error! Status: ${response.status}`);

      fullData = await response.json();

      // build mapping
      pathToVideoIdMap.clear();
      videoIdToAllFramesMap.clear();
      if (fullData?.video_results?.length) {
        fullData.video_results.forEach((v) => {
          videoIdToAllFramesMap.set(v.video_id, v.all_frames || []);
          (v.all_frames || []).forEach((p) => {
            pathToVideoIdMap.set(p, v.video_id);
          });
          (v.frames || []).forEach((f) => {
            if (f?.path) pathToVideoIdMap.set(f.path, v.video_id);
          });
        });
      }

      renderGallery();
    } catch (error) {
      console.error("Fetch error:", error);
      gallery.innerHTML = '<p class="placeholder">Failed to fetch results.</p>';
    }
  }

  // --- Render gallery ---
  function renderGallery() {
    if (!fullData) return;
    if (currentViewMode === "frame") {
      viewModeToggle.textContent = "View by Video";
      displayFrameResults(fullData.frame_results);
    } else {
      viewModeToggle.textContent = "View by Frame";
      displayVideoResults(fullData.video_results);
    }
  }

  // --- Hiển thị theo frame ---
  function displayFrameResults(frameResults) {
    gallery.innerHTML = "";
    if (!frameResults || frameResults.length === 0) {
      gallery.innerHTML = '<p class="placeholder">No results found.</p>';
      return;
    }
    gallery.className = "gallery gallery-frame-mode";

    frameResults.forEach((item) => {
      const imgElement = document.createElement("img");
      imgElement.src = addHost(item.path);
      imgElement.alt = item.path;
      imgElement.loading = "lazy";
      imgElement.dataset.pathNormalized = item.path;

      const maybeVideoId = pathToVideoIdMap.get(item.path);
      if (maybeVideoId) imgElement.dataset.videoId = maybeVideoId;

      gallery.appendChild(imgElement);
    });
  }

  // --- Parse video/frame từ path ---
  function parseVideoAndFrame(path) {
    if (!path) return { videoId: "-", frameId: "-" };
    const normalized = path.replace(/\\/g, "/");
    const parts = normalized.split("/");
    const videoId = parts[parts.length - 2] || "-";
    const filename = parts[parts.length - 1] || "";
    const frameId = filename.split(".")[0] || "-";
    return { videoId, frameId };
  }

  // --- Hiển thị theo video ---
  function displayVideoResults(videoResults) {
    gallery.innerHTML = "";
    if (!videoResults || videoResults.length === 0) {
      gallery.innerHTML = '<p class="placeholder">No results found.</p>';
      return;
    }
    gallery.className = "gallery gallery-video-mode";

    videoResults.forEach((video) => {
      const videoGroup = document.createElement("div");
      videoGroup.className = "video-group";

      const title = document.createElement("h3");
      title.className = "video-title";
      title.textContent = `Video: ${
        video.video_id
      } (Score: ${video.video_score.toFixed(3)})`;
      videoGroup.appendChild(title);

      let groupIndex = 0;
      const mainImg = document.createElement("img");
      const bestFrame = video.frames?.length > 0 ? video.frames[0].path : null;

      if (
        bestFrame &&
        Array.isArray(video.all_frames) &&
        video.all_frames.length
      ) {
        groupIndex = video.all_frames.indexOf(bestFrame);
        if (groupIndex === -1) groupIndex = 0;
        mainImg.src = addHost(video.all_frames[groupIndex]);
      } else if (Array.isArray(video.all_frames) && video.all_frames.length) {
        mainImg.src = addHost(video.all_frames[groupIndex]);
      }

      mainImg.className = "main-frame";
      mainImg.dataset.videoId = video.video_id;
      mainImg.dataset.pathNormalized = video.all_frames?.[groupIndex] || "";

      videoGroup.appendChild(mainImg);

      // Nút điều hướng
      const prevBtn = document.createElement("button");
      prevBtn.textContent = "<";
      prevBtn.className = "nav-btn left-btn";
      const nextBtn = document.createElement("button");
      nextBtn.textContent = ">";
      nextBtn.className = "nav-btn right-btn";

      function updateMainImg(newIndex) {
        groupIndex = newIndex;
        const p = video.all_frames[groupIndex];
        mainImg.src = addHost(p);
        mainImg.dataset.pathNormalized = p;
        renderThumbs();
      }

      prevBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (video.all_frames?.length > 0) {
          updateMainImg(
            (groupIndex - 1 + video.all_frames.length) % video.all_frames.length
          );
        }
      });

      nextBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (video.all_frames?.length > 0) {
          updateMainImg((groupIndex + 1) % video.all_frames.length);
        }
      });

      videoGroup.appendChild(prevBtn);
      videoGroup.appendChild(nextBtn);

      // Thumbnails lân cận
      const thumbsContainer = document.createElement("div");
      thumbsContainer.className = "neighbor-frames";
      videoGroup.appendChild(thumbsContainer);

      function renderThumbs() {
        thumbsContainer.innerHTML = "";
        const list = video.all_frames || [];
        const total = list.length;
        if (!total) return;

        let start = Math.max(0, groupIndex - 2);
        let end = Math.min(total - 1, groupIndex + 2);
        if (end - start < 4) {
          start = Math.max(0, end - 4);
          end = Math.min(total - 1, start + 4);
        }

        for (let i = start; i <= end; i++) {
          const thumb = document.createElement("img");
          const p = list[i];
          thumb.src = addHost(p);
          if (i === groupIndex) thumb.classList.add("active");
          thumb.dataset.videoId = video.video_id;
          thumb.dataset.pathNormalized = p;
          thumb.addEventListener("click", (e) => {
            e.stopPropagation();
            updateMainImg(i);
          });
          thumbsContainer.appendChild(thumb);
        }
      }
      renderThumbs();

      gallery.appendChild(videoGroup);
    });
  }

  // --- Sự kiện ---
  searchButton.addEventListener("click", performSearch);
  queryInput.addEventListener("keypress", (event) => {
    if (event.key === "Enter") performSearch();
  });
  viewModeToggle.addEventListener("click", () => {
    if (!fullData) return;
    currentViewMode = currentViewMode === "frame" ? "video" : "frame";
    renderGallery();
  });

  // --- Modal ---
  const modal = document.getElementById("image-modal");
  const modalImg = document.getElementById("modal-img");
  const modalClose = document.querySelector(".modal-close");
  const modalThumbs = document.getElementById("modal-thumbs");
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const modalPanel = modal.querySelector(".modal-panel");

  let allImages = [];
  let currentIndex = 0;

  // Click ảnh trong gallery -> mở modal
  gallery.addEventListener("click", (e) => {
    if (e.target.tagName !== "IMG") return;

    const clickedRelPath =
      e.target.dataset.pathNormalized || normalizePathFromSrc(e.target.src);
    const clickedVideoId =
      e.target.dataset.videoId || pathToVideoIdMap.get(clickedRelPath);

    if (clickedVideoId && videoIdToAllFramesMap.has(clickedVideoId)) {
      const listRel = videoIdToAllFramesMap.get(clickedVideoId) || [];
      if (listRel.length > 0) {
        allImages = listRel.map(addHost);
        let idx = listRel.indexOf(clickedRelPath);
        if (idx < 0) {
          idx = listRel.findIndex(
            (p) => addHost(p) === e.target.src || e.target.src.endsWith(p)
          );
        }
        currentIndex = Math.max(0, idx);
      } else {
        allImages = [e.target.src];
        currentIndex = 0;
      }
    } else {
      allImages = Array.from(gallery.querySelectorAll("img")).map(
        (img) => img.src
      );
      currentIndex = allImages.indexOf(e.target.src);
      if (currentIndex < 0) currentIndex = 0;
    }

    openModal(currentIndex);
  });

  function openModal(index = 0) {
    if (!Array.isArray(allImages) || allImages.length === 0) {
      console.warn("openModal: allImages rỗng");
      return;
    }
    currentIndex = Math.max(0, Math.min(index, allImages.length - 1));
    modal.style.display = "flex";
    showImage(currentIndex);
  }

  function showImage(index) {
    if (!Array.isArray(allImages) || allImages.length === 0) return;
    currentIndex = Math.max(0, Math.min(index, allImages.length - 1));
    const imgSrc = allImages[currentIndex];
    if (!imgSrc) return;

    modalImg.src = imgSrc;
    const normalizedPath = normalizePathFromSrc(imgSrc);
    const { videoId, frameId } = parseVideoAndFrame(normalizedPath);
    document.getElementById("info-videoid").textContent = videoId;
    document.getElementById("info-frame").textContent = frameId;
    renderNeighbors();
  }

  function renderNeighbors() {
    modalThumbs.innerHTML = "";
    const total = allImages.length;
    const start = Math.max(0, currentIndex - 20);
    const end = Math.min(total - 1, currentIndex + 20);

    for (let i = start; i <= end; i++) {
      if (i === currentIndex) continue;
      const thumb = document.createElement("img");
      thumb.src = allImages[i];
      thumb.addEventListener("click", (e) => {
        e.stopPropagation();
        showImage(i);
      });
      modalThumbs.appendChild(thumb);
    }
  }

  prevBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (currentIndex > 0) showImage(currentIndex - 1);
  });
  nextBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (currentIndex < allImages.length - 1) showImage(currentIndex + 1);
  });

  document.addEventListener("keydown", (e) => {
    if (modal.style.display !== "flex") return;
    if (e.key === "ArrowLeft" && currentIndex > 0) {
      showImage(currentIndex - 1);
    } else if (e.key === "ArrowRight" && currentIndex < allImages.length - 1) {
      showImage(currentIndex + 1);
    } else if (e.key === "Escape") {
      modal.style.display = "none";
    }
  });

  modalClose.addEventListener("click", (e) => {
    e.stopPropagation();
    modal.style.display = "none";
  });
  modal.addEventListener("click", () => (modal.style.display = "none"));
  modalPanel.addEventListener("click", (e) => e.stopPropagation());
});
