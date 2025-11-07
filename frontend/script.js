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
  const SubmitButton = document.getElementById("submit-btn");
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

  // Bắt sự kiện cho nút mở YouTube (ĐÃ SỬA ĐỂ GIỐNG CODE 1)
  document.getElementById("open-youtube-btn").addEventListener("click", () => {
    const videoId = document.getElementById("info-videoid").innerText.trim();
    const frameIndex = parseInt(
      document.getElementById("info-frame").innerText.trim()
    );

    if (videoData && videoData[videoId]) {
      // Gọi hàm mở modal tùy chỉnh, thay vì mở tab mới
      openYouTubeModal(videoId, frameIndex);
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
    let query = queryInput.value.trim();
    const k = topkInput.value;
    let colors = colorInput.value.trim();
    let ocr = ocrInput.value.trim();
    const modeSelect = document.getElementById("model-select");
    // VẪN GIỮ NGUYÊN LOGIC CỦA CODE 2
    const mode = modeSelect.value || "SIGLIP_COLLECTION"; 
    if(!query){
      query = "a"
    }
if(!colors){
      colors = "a"
    }
    if(!ocr){
      ocr = "a"
    }
    gallery.innerHTML = '<p class="placeholder">Loading...</p>';

    let apiUrl = `${HOST}/search?query=${encodeURIComponent(query)}&k=${k}&mode=${mode}&colors=${encodeURIComponent(colors)}&ocr=${encodeURIComponent(ocr)}`;


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
  //------------------------get sessionID ------------------------------
 async function get_sessionID(){
      console.log("BÊN TRONG FUNCTION!");
   return fetch("https://eventretrieval.oj.io.vn/api/v2/login", {
    method: "POST",  // Phương thức POST
    headers: {
        "Content-Type": "application/json", // Đảm bảo bạn gửi dữ liệu JSON
    },
    body: JSON.stringify({  // Dữ liệu bạn muốn gửi đi
        username: "team059",
        password: "ejFN4kxfqw"
    })
    })
    .then(response => response.json())  // Chuyển đổi kết quả trả về thành JSON
    .then(result => {
        console.log("✅ Server Responsaaaaaaaae:");
        console.log("result", result)

        window.session_id = result.sessionId;
        return result.sessionId;
    })
    .catch(error => {
        console.error("❌ Error:", error);  // In lỗi nếu có
    });
}


//----------------get evaluationID-----------------------

async function get_evaluationID(session_id){
      console.log("BÊN TRONG FUNCTION EVALUATIONID!");
  return fetch(`https://eventretrieval.oj.io.vn/api/v2/client/evaluation/list?session=${session_id}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json"
    }
  })
  .then(response => response.json())
  .then(result => {
    console.log("✅ Server Response (Evaluation):", result);

    // Kiểm tra xem có evaluation nào active không
    if (Array.isArray(result) && result.length > 0) {
      let evaluationId = result[1].id;
      console.log("🎯 Evaluation ID:", evaluationId);

      // Lưu lại để dùng khi submit bài
      
       return evaluationId

      // Tùy chọn: tự động gọi submitAnswer() sau khi lấy được ID
      // submitAnswer(evaluationId, sessionId);
    } else {
      console.warn("⚠️ Không tìm thấy evaluation nào đang ACTIVE!");
    }
  })
  .catch(error => {
    console.error("❌ Lỗi khi lấy evaluation:", error);
  });

}

// async function submit(session_id, evaluation_id, body1) {
//     try {
//         // Kiểm tra body trước khi gửi đi
//         if (!body1) {
//             throw new Error("Body is required");
//         }

//         console.log("BÊN TRONG FUNCTION SUBMIT!");
//         console.log(`https://eventretrieval.oj.io.vn/api/v2/submit/${evaluation_id}?session=${session_id}`);
//         console.log("body: BÊN TRONG SUBMIT", body1);

//         const response = await fetch(`https://eventretrieval.oj.io.vn/api/v2/submit/${evaluation_id}?session=${session_id}`, {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({
//                 session_id: session_id,
//                 evaluation_id: evaluation_id,
//                 body: JSON.stringify(body1)
//             })
//         });

//         const result = await response.json(); // Đảm bảo nhận được kết quả từ server
//         alert("🎉 Nộp bài thành công!",result);
//     } catch (error) {
//         console.error("❌ Error:", error);
//         alert("Lỗi khi gửi dữ liệu lên server!");
//     }
// }

async function submit(session_id, evaluation_id, body) {
    try {
        const response = await fetch("http://127.0.0.1:5000/submit-data", { // URL của server Python (Flask)
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                session_id: session_id,
                evaluation_id: evaluation_id,
                answer_data: body
            })
        });

        const result = await response.json();
        if (response.ok) {
            console.log("Nộp bài thành công!", result);
        } else {
            console.error("Lỗi khi nộp bài:", result);
        }
    } catch (error) {
        console.error("Error in submitting data:", error);
    }
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
  
  // --- Submit button ---
SubmitButton.addEventListener("click", async function() {
  
    // Lấy giá trị từ các phần tử giao diện
    const videoId = document.getElementById("info-videoid").textContent.trim();
    const frameIndex = parseInt(document.getElementById("info-frame").textContent.trim());
    console.log("VIDEOID", videoId);
    console.log("frameIndex", frameIndex);
     
    // Lấy dữ liệu từ các ô nhập liệu loại bỏ khoảng trắng
    const QA = document.getElementById("QA_input").value.trim().toUpperCase();
    const TRAKE = document.getElementById("TRAKE_input").value.trim();

    // Xác định loại truy vấn
    let queryType = "video_kis";
    let dataToSubmit  = "";


    if (QA !== "") {
        queryType = "qa";
        dataToSubmit = QA;
    } else if (TRAKE !== "") {
        queryType = "trake";
        dataToSubmit = TRAKE;
    }else{
      queryType = "video_kis"
    }

    // Nếu không có dữ liệu nào được nhập

    //--------------------------------------------------------------------------------------------------------

    //--------------------------------------------------------------------------------------------------------

 console.log("📡 GỌI API LẤY EVALUATION...");

 console.log("đây là sessionID");
  let session_id = await get_sessionID()
  console.log("SESSID",session_id)
  // Gọi đến Flask backend
let evaluation_id = await get_evaluationID(session_id)
// ------------------------------------------------------------------------------

    let videoInfo = videoData[videoId];
    currentVideoFps = videoInfo.fps;
    // --- Xây dựng body theo chuẩn DRES ---
     console.log(currentVideoFps,"FPS BÊN TRONG MOI THG CURRRENTFPS")

    let body = {};
let start = parseInt(parseInt(frameIndex) / parseInt(currentVideoFps) * 1000);
console.log("start", start);
    if (queryType === "video_kis") {
        body = {
            answerSets: [{
                answers: [{
                    mediaItemName: videoId,
                    start: `${start}`,  // nếu 30fps: mỗi frame ~33.33ms
                    end: `${start}`
                }]
            }]
        };
    } else if (queryType === "qa") {
        body = {
            answerSets: [{
                answers: [{
                    text: `QA-${dataToSubmit}-${videoId}-${start}`
                }]
            }]
        };
    } else if (queryType === "trake") {
        body = {
            answerSets: [{
                answers: [{
                    text: `TR-${videoId}-${dataToSubmit}`
                }]
            }]
        };
    }
console.log("BODY TRUCWCS KHI VÀO SUBMIT", body);
    // --- Gửi dữ liệu đến backend (Flask app.py) ---
await submit(session_id,evaluation_id,body);

  });

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

  // === PHẦN ĐƯỢC THÊM VÀO TỪ CODE 1 ===
  const youtubeModal = document.getElementById("youtube-modal");
  const youtubeIframe = document.getElementById("youtube-iframe");
  const youtubeModalClose = document.querySelector(".youtube-modal-close");
  const ytFrameNumber = document.getElementById("yt-frame-number");
  const ytFrameTime = document.getElementById("yt-frame-time");
  const ytFrameFps = document.getElementById("yt-frame-fps");
  console.log(ytFrameFps,"FPS")
  const ytCopyBtn = document.getElementById("yt-copy-btn");

  let ytPlayer = null;
  let ytUpdateInterval = null;
  let currentVideoFps = 30;
  let currentVideoId = null;
  let isYTAPIReady = false;

  // Load YouTube IFrame API
  function loadYouTubeAPI() {
    if (window.YT && window.YT.Player) {
      isYTAPIReady = true;
      return;
    }

    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    const firstScriptTag = document.getElementsByTagName("script")[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
  }

  // YouTube API ready callback
  window.onYouTubeIframeAPIReady = function () {
    isYTAPIReady = true;
    console.log("YouTube API Ready!");
  };

  // Load API on page load
  loadYouTubeAPI();

  function openYouTubeModal(videoId, frameIndex) {
    if (!videoData[videoId]) return;

    const videoInfo = videoData[videoId];
    currentVideoFps = videoInfo.fps || 30;
    currentVideoId = videoId;

    // Extract YouTube video ID from URL
    const url = videoInfo.watch_url;
    const youtubeId = extractYouTubeId(url);
    if (!youtubeId) {
      alert("Invalid YouTube URL!");
      return;
    }

    // Calculate start time
    const startSeconds = Math.floor(frameIndex / currentVideoFps);

    // Update FPS display
    ytFrameFps.textContent = `FPS: ${currentVideoFps}`;
    ytFrameNumber.textContent = "Frame: Loading...";
    ytFrameTime.textContent = "Time: Loading...";

    // Show modal
    youtubeModal.style.display = "flex";

    // Initialize YouTube player
    if (isYTAPIReady && window.YT && window.YT.Player) {
      initYouTubePlayer(youtubeId, startSeconds);
    } else {
      // Fallback: use simple iframe
      const embedUrl = `https://www.youtube.com/embed/${youtubeId}?start=${startSeconds}&rel=0`;
      youtubeIframe.src = embedUrl;
      ytFrameNumber.textContent = "Frame: API not ready";
      ytFrameTime.textContent = "Time: Use video controls";
    }
  }

  function initYouTubePlayer(youtubeId, startSeconds) {
    // Destroy existing player if any
    if (ytPlayer) {
      ytPlayer.destroy();
    }

    ytPlayer = new YT.Player("youtube-iframe", {
      height: "100%",
      width: "100%",
      videoId: youtubeId,
      playerVars: {
        start: startSeconds,
        autoplay: 1,
        controls: 1,
        rel: 0,
        modestbranding: 1,
      },
      events: {
        onReady: onPlayerReady,
        onStateChange: onPlayerStateChange,
      },
    });
  }

  function onPlayerReady(event) {
    console.log("YouTube Player Ready!");
    startFrameTracking();
  }

  function onPlayerStateChange(event) {
    // Player state: -1 (unstarted), 0 (ended), 1 (playing), 2 (paused), 3 (buffering), 5 (cued)
    if (event.data === YT.PlayerState.PLAYING) {
      startFrameTracking();
    } else if (
      event.data === YT.PlayerState.PAUSED ||
      event.data === YT.PlayerState.ENDED
    ) {
      updateFrameDisplay();
    }
  }

  function extractYouTubeId(url) {
    const regExp =
      /^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#&?]*).*/;
    const match = url.match(regExp);
    return match && match[7].length === 11 ? match[7] : null;
  }

  function startFrameTracking() {
    // Clear existing interval
    if (ytUpdateInterval) {
      clearInterval(ytUpdateInterval);
    }

    // Update frame display every 100ms for smooth updates
    ytUpdateInterval = setInterval(() => {
      updateFrameDisplay();
    }, 100);
  }

  function updateFrameDisplay() {
    if (!ytPlayer || !ytPlayer.getCurrentTime) {
      return;
    }

    try {
      const currentTime = ytPlayer.getCurrentTime();
      if (currentTime === undefined || currentTime === null) return;

      // Calculate frame number
      const frameNumber = Math.floor(currentTime * currentVideoFps);

      // Format time
      const hours = Math.floor(currentTime / 3600);
      const minutes = Math.floor((currentTime % 3600) / 60);
      const seconds = Math.floor(currentTime % 60);
      const milliseconds = Math.floor((currentTime % 1) * 1000);

      // Update display
      ytFrameNumber.textContent = `Frame: ${frameNumber}`;
      ytFrameTime.textContent = `Time: ${String(hours).padStart(
        2,
        "0"
      )}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(
        2,
        "0"
      )}.${String(milliseconds).padStart(3, "0")}`;
    } catch (error) {
      console.error("Error updating frame:", error);
    }
  }

  // Copy button handler
  ytCopyBtn.addEventListener("click", () => {
    const frameText = ytFrameNumber.textContent.replace("Frame: ", "").trim();
    const ytCopyBtn = document.getElementById("yt-copy-btn");

    if (frameText && !isNaN(frameText)) {
      navigator.clipboard
        .writeText(frameText)
        .then(() => {
          const originalText = ytCopyBtn.textContent;
          ytCopyBtn.textContent = "✅ Copied!";
          ytCopyBtn.style.background = "#ffcc00";
          
          // Append nội dung vào input có id "TRAKE_input"
          const inputElement = document.getElementById("TRAKE_input");

        // Kiểm tra và xóa dấu phẩy cuối cùng nếu có
        let currentValue = inputElement.value;
        if (currentValue.endsWith(',')) {
          currentValue = currentValue.slice(0, -1); // Xóa dấu phẩy cuối cùng
        }

        // Nếu input có nội dung, thêm dấu cộng trước frameText, nếu không thì chỉ thêm frameText
        if (currentValue) {
          inputElement.value = currentValue + "," + frameText;  // Thêm dấu cộng giữa các giá trị
        } else {
          inputElement.value = frameText;  // Nếu input trống, chỉ thêm frameText
        }

          setTimeout(() => {
            ytCopyBtn.textContent = originalText;
            ytCopyBtn.style.background = "#00ff00";
          }, 1000);
        })
        .catch(() => {
          ytCopyBtn.textContent = "❌ Failed";
          setTimeout(() => {
            ytCopyBtn.textContent = "📋 Copy Frame";
          }, 1000);
        });
    } else {
      alert("Frame number not available yet!");
    }
});

  // Close modal handlers
  youtubeModalClose.addEventListener("click", (e) => {
    e.stopPropagation();
    closeYouTubeModal();
  });

  youtubeModal.addEventListener("click", (e) => {
    if (e.target === youtubeModal) {
      closeYouTubeModal();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (youtubeModal.style.display === "flex" && e.key === "Escape") {
      closeYouTubeModal();
    }
  });

  function closeYouTubeModal() {
    youtubeModal.style.display = "none";

    // Stop player
    if (ytPlayer && ytPlayer.stopVideo) {
      ytPlayer.stopVideo();
    }

    // Clear interval
    if (ytUpdateInterval) {
      clearInterval(ytUpdateInterval);
      ytUpdateInterval = null;
    }

    // Destroy player
    if (ytPlayer && ytPlayer.destroy) {
      ytPlayer.destroy();
      ytPlayer = null;
    }

    // Reset iframe
    youtubeIframe.src = "";
  }
  // === HẾT PHẦN THÊM VÀO ===
});
// Thêm sự kiện cho nút Clear
document.getElementById("clear-btn").addEventListener("click", () => {
    // Lấy các ô input
    const trakeInput = document.getElementById("TRAKE_input");
    const qaInput = document.getElementById("QA_input");

    // Xóa giá trị trong các ô input
    trakeInput.value = "";
    qaInput.value = "";
});

document.getElementById("clearall-btn").addEventListener("click", () => {
    // Lấy các ô input
    const ocrinput = document.getElementById("ocr-input");
    const asrinput = document.getElementById("color-input");
    const clipinput = document.getElementById("query-input");
    // Xóa giá trị trong các ô input
    ocrinput.value = "";
    asrinput.value = "";
    clipinput.value = "";
});