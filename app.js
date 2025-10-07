// Application State
const AppState = {
    isLive: false,
    currentSubject: null,
    searchQuery: '',
    sortBy: 'latest',
    theme: 'light',
    videos: {},
    schedule: [], // Will be populated from schedule.json
    filteredVideos: [],
    clockInterval: null
};

// DOM Elements
const elements = {
    liveStatus: document.getElementById('liveStatus'),
    statusDot: document.getElementById('statusDot'),
    statusText: document.getElementById('statusText'),
    currentTime: document.getElementById('currentTime'),
    timeValue: document.getElementById('timeValue'),
    liveSection: document.getElementById('liveSection'),
    offlineMessage: document.getElementById('offlineMessage'),
    videoLibrary: document.getElementById('videoLibrary'),
    videoGrid: document.getElementById('videoGrid'),
    searchInput: document.getElementById('searchInput'),
    searchBtn: document.getElementById('searchBtn'),
    refreshBtn: document.getElementById('refreshBtn'),
    themeToggle: document.getElementById('themeToggle'),
    sortSelect: document.getElementById('sortSelect'),
    subjectTabsContainer: document.getElementById('subjectTabsContainer'),
    videoModal: document.getElementById('videoModal'),
    modalOverlay: document.getElementById('modalOverlay'),
    modalClose: document.getElementById('modalClose'),
    modalTitle: document.getElementById('modalTitle'),
    modalDuration: document.getElementById('modalDuration'),
    modalDate: document.getElementById('modalDate'),
    modalStartTime: document.getElementById('modalStartTime'),
    noResults: document.getElementById('noResults'),
    nextStreamInfo: document.getElementById('nextStreamInfo'),
    nextStreamDay: document.getElementById('nextStreamDay'),
    nextStreamSubject: document.getElementById('nextStreamSubject'),
    countdownValue: document.getElementById('countdownValue'),
    loadingIndicator: document.getElementById('loadingIndicator'),
};

// Initialize Application
function initApp() {
    Promise.all([
        fetch('videos.json').then(res => res.json()),
        fetch('schedule.json').then(res => res.json())
    ])
    .then(([videoData, scheduleData]) => {
        AppState.videos = {};
        videoData.forEach(video => {
            if (!AppState.videos[video.subject]) AppState.videos[video.subject] = [];
            AppState.videos[video.subject].push(video);
        });
        AppState.schedule = scheduleData;

        populateSubjectTabs();
        loadUserPreferences();
        setupEventListeners();
        startClock();
    })
    .catch(error => {
        console.error("Could not load initial data:", error);
        elements.videoLibrary.innerHTML = `<p style="text-align:center;">Could not load page data. Please try again later.</p>`;
    });
}

function populateSubjectTabs() {
    elements.subjectTabsContainer.innerHTML = '';
    const subjects = Object.keys(AppState.videos);
    if (subjects.length === 0) {
        elements.subjectTabsContainer.innerHTML = '<p>No video subjects found in the library.</p>';
        return;
    }
    AppState.currentSubject = subjects[0];
    subjects.forEach(subject => {
        const button = document.createElement('button');
        button.className = 'tab-button';
        button.dataset.subject = subject;
        button.textContent = subject;
        if (subject === AppState.currentSubject) button.classList.add('active');
        button.addEventListener('click', () => handleSubjectChange(subject));
        elements.subjectTabsContainer.appendChild(button);
    });
    filterAndDisplayVideos();
}

function loadUserPreferences() {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    AppState.theme = localStorage.getItem('theme') || (prefersDark ? 'dark' : 'light');
    applyTheme();
}

function applyTheme() {
    document.documentElement.setAttribute('data-color-scheme', AppState.theme);
    updateThemeToggleIcon();
}

function updateThemeToggleIcon() {
    const icon = AppState.theme === 'dark' ? '🌙' : '☀️';
    elements.themeToggle.innerHTML = `${icon} Theme`;
}

function setupEventListeners() {
    elements.searchInput.addEventListener('input', handleSearch);
    elements.searchBtn.addEventListener('click', handleSearch);
    elements.refreshBtn.addEventListener('click', () => location.reload());
    elements.themeToggle.addEventListener('click', toggleTheme);
    elements.sortSelect.addEventListener('change', handleSortChange);
    elements.modalClose.addEventListener('click', closeVideoModal);
    elements.modalOverlay.addEventListener('click', closeVideoModal);
    document.addEventListener('keydown', e => e.key === 'Escape' && closeVideoModal());
}

function startClock() {
    updateClock();
    AppState.clockInterval = setInterval(updateClock, 1000);
}

function updateClock() {
    const now = new Date();
    const istTime = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
    elements.timeValue.textContent = istTime.toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const istHour = istTime.getHours();
    const istDay = istTime.getDay();
    AppState.isLive = (istHour >= 9 && istHour < 11 && istDay > 0 && istDay < 7);
    updateLiveStatus();
    updateNextStreamInfo();
}

function updateLiveStatus() {
    const livePlayerDiv = document.getElementById('livePlayer');
    if (!elements.liveSection || !elements.offlineMessage || !livePlayerDiv) return;
    if (AppState.isLive) {
        elements.liveSection.classList.remove('hidden');
        elements.offlineMessage.classList.add('hidden');
        if (livePlayerDiv.querySelector('iframe') === null) {
            const iframe = document.createElement('iframe');
            iframe.src = "https://www.youtube.com/embed/live_stream?channel=UC4h_7L2n2aC_j-gN-V_f_xw&autoplay=1&mute=1";
            iframe.frameBorder = "0";
            iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
            iframe.allowFullscreen = true;
            livePlayerDiv.appendChild(iframe);
        }
    } else {
        elements.liveSection.classList.add('hidden');
        elements.offlineMessage.classList.remove('hidden');
        livePlayerDiv.innerHTML = '';
    }
}

function updateNextStreamInfo() {
    if (AppState.isLive || !elements.nextStreamInfo) return;
    const now = new Date();
    let nextStream = null;
    for (const stream of AppState.schedule) {
        const streamTime = new Date(stream.startTime);
        if (streamTime > now) {
            nextStream = stream;
            break;
        }
    }
    if (nextStream) {
        const streamTime = new Date(nextStream.startTime);
        const timeDiff = streamTime - now;
        const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((timeDiff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((timeDiff % (1000 * 60)) / 1000);
        const streamDay = streamTime.toLocaleDateString('en-GB', { weekday: 'long' });
        elements.nextStreamDay.textContent = `Next Class: ${streamDay}`;
        elements.nextStreamSubject.textContent = `Topic: ${nextStream.title}`;
        let countdownString = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        if (days > 0) countdownString = `${days}d ${countdownString}`;
        elements.countdownValue.textContent = countdownString;
    } else {
        elements.nextStreamDay.textContent = 'No upcoming classes';
        elements.nextStreamSubject.textContent = 'Please check back later for updates.';
        elements.countdownValue.textContent = '--:--:--';
    }
}

function filterAndDisplayVideos() {
    if (!AppState.currentSubject) {
        elements.videoGrid.innerHTML = '';
        elements.noResults.classList.add('hidden');
        return;
    }
    const currentVideos = AppState.videos[AppState.currentSubject] || [];
    let filtered = currentVideos.filter(video => !AppState.searchQuery || video.title.toLowerCase().includes(AppState.searchQuery));
    filtered = sortVideos(filtered);
    AppState.filteredVideos = filtered;
    displayVideos(filtered);
}

function sortVideos(videos) {
    return videos.sort((a, b) => {
        switch (AppState.sortBy) {
            case 'alphabetical': return a.title.localeCompare(b.title);
            case 'duration': return parseDuration(b.duration) - parseDuration(a.duration);
            default: return new Date(b.uploadDate) - new Date(a.uploadDate);
        }
    });
}

function displayVideos(videos) {
    if (videos.length === 0) {
        elements.videoGrid.classList.add('hidden');
        elements.noResults.classList.remove('hidden');
        return;
    }
    elements.videoGrid.classList.remove('hidden');
    elements.noResults.classList.add('hidden');
    elements.videoGrid.innerHTML = videos.map(video => createVideoCard(video)).join('');
    elements.videoGrid.querySelectorAll('.video-card').forEach(card => {
        card.addEventListener('click', () => {
            const videoId = card.dataset.videoId;
            const video = AppState.filteredVideos.find(v => v.id === videoId);
            if (video) openVideoModal(video);
        });
    });
}

function createVideoCard(video) {
    const uploadDate = formatDate(video.uploadDate);
    const subjectColor = getSubjectColor(video.subject);
    return `<div class="video-card" data-video-id="${video.id}"><div class="video-thumbnail" style="background: ${subjectColor}"><div class="thumbnail-placeholder">▶️</div><div class="play-overlay"><svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"></polygon></svg></div><div class="duration-badge">${video.duration}</div></div><div class="video-content"><h3 class="video-title">${video.title}</h3><div class="video-meta"><span class="video-subject">${video.subject}</span><span class="video-date">${uploadDate}</span></div></div></div>`;
}

function handleSearch() {
    AppState.searchQuery = elements.searchInput.value.trim().toLowerCase();
    filterAndDisplayVideos();
}

function toggleTheme() {
    AppState.theme = AppState.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', AppState.theme);
    applyTheme();
}

function handleSortChange() {
    AppState.sortBy = elements.sortSelect.value;
    filterAndDisplayVideos();
}

function handleSubjectChange(subject) {
    AppState.currentSubject = subject;
    elements.subjectTabsContainer.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.subject === subject);
    });
    filterAndDisplayVideos();
}

function openVideoModal(video) {
    elements.modalTitle.textContent = video.title;
    elements.modalDuration.textContent = `Duration: ${video.duration}`;
    elements.modalDate.textContent = formatDate(video.uploadDate);
    elements.modalStartTime.textContent = `Started at ${video.startTime}`;

    const player = document.getElementById('modalPlayer');

    // Show loading indicator
    elements.loadingIndicator.classList.remove('hidden');

    // Set the iframe src to the Google Drive preview URL
    if (video.gdrive_url) {
        player.src = video.gdrive_url;
        // Hide loading when iframe loads
        player.onload = () => {
            elements.loadingIndicator.classList.add('hidden');
        };
    } else {
        player.src = '';
        elements.loadingIndicator.classList.add('hidden');
    }

    elements.videoModal.classList.remove('hidden');
    elements.videoModal.classList.add('fade-in');
    document.body.style.overflow = 'hidden';
}

function closeVideoModal() {
    const player = document.getElementById('modalPlayer');
    player.src = '';
    elements.loadingIndicator.classList.add('hidden');
    elements.videoModal.classList.add('hidden');
    document.body.style.overflow = '';
}

function parseDuration(duration) {
    if (!duration || typeof duration !== 'string') return 0;
    const parts = duration.split(':').map(Number);
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    return 0;
}

function getSubjectColor(subject) {
    const colors = {'Geography': 'var(--color-bg-1)','Polity': 'var(--color-bg-2)','Economy': 'var(--color-bg-3)','History': 'var(--color-bg-4)','Science': 'var(--color-bg-5)','Maths': 'var(--color-bg-6)','English': 'var(--color-bg-7)','Reasoning': 'var(--color-bg-8)','Others': 'var(--color-bg-1)'};
    return colors[subject] || 'var(--color-bg-1)';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

document.addEventListener('DOMContentLoaded', initApp);
