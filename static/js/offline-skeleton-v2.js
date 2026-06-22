/**
 * PwaniNet Offline Skeleton Manager v3
 * Page-aware skeletons using new skeleton HTML files
 * Detects all page types and loads relevant skeletons
 */
(function(){
'use strict';

var overlayId='offline-skeleton-overlay',isShowing=false;

function detectPageType(){
  var p=window.location.pathname;
  if(p.includes('/profile/')||p.match(/^\/users\/[^\/]+\/?$/))return'profile';
  if(p.includes('/groups/')&&!p.includes('/create')){
    if(p.match(/\/groups\/[^\/]+\/?$/))return'group-detail';
    return'groups';
  }
  if(p.includes('/notifications/'))return'notifications';
  if(p.includes('/posts/')&&p.match(/\/posts\/[^\/]+\/?$/))return'post-detail';
  if(p.includes('/courses/')&&p.match(/\/courses\/[^\/]+\/?$/))return'course-detail';
  if(p.includes('/search')||p.includes('?q='))return'search';
  if(p.includes('/messages/')){
    if(p.match(/\/messages\/[^\/]+\/?$/))return'messaging-detail';
    return'messaging-list';
  }
  if(p==='/'||p==='/home/'||p.includes('/posts/'))return'home';
  return'home';
}

async function buildHTML(type){
  if(type==='messages')return'';
  
  // Try to load HTML template first for consistency with page load skeleton
  try{
    const templateUrl=getSkeletonTemplateUrl(type);
    const response=await fetch(templateUrl);
    if(response.ok){
      const html=await response.text();
      // Wrap with offline banner
      return '<div id="'+overlayId+'" data-page="'+type+'">'+
        '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
        html+
      '</div>';
    }
  }catch(e){
    console.log('[OfflineSkeleton] Template fetch failed, using fallback:',e);
  }
  
  // Fallback to inline generation
  if(type==='profile')return buildProfileSkeleton();
  if(type==='groups')return buildGroupsSkeleton();
  if(type==='group-detail')return buildGroupDetailSkeleton();
  if(type==='notifications')return buildNotificationsSkeleton();
  if(type==='post-detail')return buildPostDetailSkeleton();
  if(type==='course-detail')return buildCourseDetailSkeleton();
  if(type==='messaging-list')return buildMessagingListSkeleton();
  if(type==='messaging-detail')return buildMessagingDetailSkeleton();
  if(type==='search')return buildSearchResultsSkeleton();
  return buildHomeSkeleton();
}

function getSkeletonTemplateUrl(type){
  const templateMap={
    'home':'/skeleton-template/_skeleton_post_feed.html',
    'profile':'/skeleton-template/_skeleton_profile.html',
    'groups':'/skeleton-template/_skeleton_groups_list.html',
    'group-detail':'/skeleton-template/_skeleton_group_detail.html',
    'notifications':'/skeleton-template/_skeleton_notifications.html',
    'post-detail':'/skeleton-template/_skeleton_post_detail.html',
    'course-detail':'/skeleton-template/_skeleton_course_detail.html',
    'messaging-list':'/skeleton-template/_skeleton_messaging_list.html',
    'messaging-detail':'/skeleton-template/_skeleton_messaging_detail.html',
    'search':'/skeleton-template/_skeleton_search_results.html'
  };
  return templateMap[type]||templateMap['home'];
}

function buildHomeSkeleton(){
  return '<div id="'+overlayId+'" data-page="home">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<div class="home-skeleton-container">'+
      '<div class="card search-row">'+
        '<div class="search-avatar sk"></div>'+
        '<div class="search-bar sk"></div>'+
      '</div>'+
      '<div class="explore-head">'+
        '<div class="et sk"></div>'+
        '<div class="ev sk"></div>'+
      '</div>'+
      '<div class="explore-row">'+
        '<div class="explore-item"><div class="explore-circle sk"></div><div class="explore-label sk"></div></div>'+
        '<div class="explore-item"><div class="explore-circle sk"></div><div class="explore-label sk"></div></div>'+
        '<div class="explore-item"><div class="explore-circle sk"></div><div class="explore-label sk"></div></div>'+
        '<div class="explore-item"><div class="explore-circle sk"></div><div class="explore-label sk"></div></div>'+
        '<div class="explore-item"><div class="explore-circle sk"></div><div class="explore-label sk"></div></div>'+
        '<div class="explore-item"><div class="explore-circle sk"></div><div class="explore-label sk"></div></div>'+
        '<div class="explore-item"><div class="explore-circle sk"></div><div class="explore-label sk"></div></div>'+
      '</div>'+
      '<div class="feed-col">'+
        buildPostCardSkeleton()+
        buildPostCardSkeleton()+
      '</div>'+
    '</div>'+
  '</div>';
}

function buildPostCardSkeleton(){
  return '<div class="card post-card">'+
    '<div class="post-head">'+
      '<div class="post-avatar sk"></div>'+
      '<div class="post-meta">'+
        '<div class="post-name sk"></div>'+
        '<div class="post-time sk"></div>'+
      '</div>'+
      '<div class="post-kebab sk"></div>'+
    '</div>'+
    '<div class="post-text sk"></div>'+
    '<div class="post-media sk"></div>'+
    '<div class="post-actions">'+
      '<div class="action w1 sk"></div><div class="action w2 sk"></div>'+
      '<div class="action w3 sk"></div><div class="action w4 sk"></div>'+
    '</div>'+
    '<div class="comment-row">'+
      '<div class="comment-avatar sk"></div>'+
      '<div class="comment-input-wrap">'+
        '<div class="comment-input sk"></div>'+
        '<div class="comment-send sk"></div>'+
      '</div>'+
    '</div>'+
  '</div>';
}

function buildProfileSkeleton(){
  return '<div id="'+overlayId+'" data-page="profile">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<div class="profile-skeleton-container">'+
      '<div class="profile-grid">'+
        '<div>'+
          '<div class="card profile-card">'+
            '<div class="cover sk"></div>'+
            '<div class="avatar-wrap"><div class="avatar sk"></div></div>'+
            '<div class="profile-body">'+
              '<div class="badge-line sk"></div>'+
              '<div class="name-line sk"></div>'+
              '<div class="handle-line sk"></div>'+
              '<div class="bio-line sk"></div>'+
              '<div class="btn-line sk"></div>'+
              '<div class="btn-line sk"></div>'+
              '<div class="btn-line sk" style="width:90%; margin:0 auto;"></div>'+
              '<div class="stats-row">'+
                '<div class="stat"><div class="num sk"></div><div class="lbl sk"></div></div>'+
                '<div class="stat"><div class="num sk"></div><div class="lbl sk"></div></div>'+
                '<div class="stat"><div class="num sk"></div><div class="lbl sk"></div></div>'+
              '</div>'+
            '</div>'+
          '</div>'+
          '<div class="card side-card">'+
            '<div class="side-title-row"><div class="side-title sk"></div></div>'+
            '<div class="side-row"><div class="k sk"></div><div class="v sk"></div></div>'+
            '<div class="side-row"><div class="k sk"></div><div class="v sk"></div></div>'+
            '<div class="side-row"><div class="k sk"></div><div class="v sk"></div></div>'+
          '</div>'+
          '<div class="card side-card">'+
            '<div class="side-title-row">'+
              '<div class="side-title sk" style="width:65%;"></div>'+
              '<div class="side-hide sk"></div>'+
            '</div>'+
            '<div class="bar sk" style="width:25%;"></div>'+
            '<div class="para-line sk"></div>'+
            '<div class="para-line sk" style="width:85%;"></div>'+
            '<div class="para-line sk" style="width:70%;"></div>'+
          '</div>'+
        '</div>'+
        '<div class="feed-col">'+
          buildPostCardSkeleton()+
        '</div>'+
      '</div>'+
    '</div>'+
  '</div>';
}

function buildGroupsSkeleton(){
  return '<div id="'+overlayId+'" data-page="groups">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<div class="groups-skeleton-container">'+
      '<div class="groups-head">'+
        '<div>'+
          '<div class="gh-eyebrow"><div class="gh-dot"></div><div class="gh-eyebrow-line sk"></div></div>'+
          '<div class="gh-title sk"></div>'+
        '</div>'+
        '<div class="gh-btn sk"></div>'+
      '</div>'+
      '<div class="groups-grid">'+
        '<div>'+
          '<div class="card your-groups">'+
            '<div class="yg-label-row"><div class="yg-icon-sm sk"></div><div class="yg-label sk"></div></div>'+
            '<div class="yg-empty">'+
              '<div class="yg-icon sk"></div>'+
              '<div class="yg-line sk"></div>'+
            '</div>'+
          '</div>'+
          '<div class="card how-card">'+
            '<div class="how-head"><div class="how-icon sk"></div><div class="how-title sk"></div></div>'+
            '<div class="para-line sk"></div>'+
            '<div class="para-line sk" style="width:90%;"></div>'+
            '<div class="para-line sk" style="width:60%;"></div>'+
          '</div>'+
        '</div>'+
        '<div>'+
          '<div class="all-groups-row">'+
            '<div class="ag-label sk"></div>'+
            '<div class="ag-count sk"></div>'+
          '</div>'+
          '<div class="group-list">'+
            '<div class="card group-card">'+
              '<div class="group-top">'+
                '<div class="group-icon sk"></div>'+
                '<div class="group-info">'+
                  '<div class="group-title-row"><div class="group-title sk"></div><div class="group-badge sk"></div></div>'+
                  '<div class="group-desc sk"></div>'+
                '</div>'+
              '</div>'+
              '<div class="group-bottom"><div class="group-count sk"></div><div class="group-view sk"></div></div>'+
            '</div>'+
            '<div class="card group-card">'+
              '<div class="group-top">'+
                '<div class="group-icon sk"></div>'+
                '<div class="group-info">'+
                  '<div class="group-title-row"><div class="group-title sk"></div><div class="group-badge sk"></div></div>'+
                  '<div class="group-desc sk"></div>'+
                '</div>'+
              '</div>'+
              '<div class="group-bottom"><div class="group-count sk"></div><div class="group-view sk"></div></div>'+
            '</div>'+
            '<div class="card group-card">'+
              '<div class="group-top">'+
                '<div class="group-icon sk"></div>'+
                '<div class="group-info">'+
                  '<div class="group-title-row"><div class="group-title sk"></div><div class="group-badge sk"></div></div>'+
                  '<div class="group-desc sk"></div>'+
                '</div>'+
              '</div>'+
              '<div class="group-bottom"><div class="group-count sk"></div><div class="group-view sk"></div></div>'+
            '</div>'+
            '<div class="card group-card">'+
              '<div class="group-top">'+
                '<div class="group-icon sk"></div>'+
                '<div class="group-info">'+
                  '<div class="group-title-row"><div class="group-title sk"></div><div class="group-badge sk"></div></div>'+
                  '<div class="group-desc sk"></div>'+
                '</div>'+
              '</div>'+
              '<div class="group-bottom"><div class="group-count sk"></div><div class="group-view sk"></div></div>'+
            '</div>'+
          '</div>'+
        '</div>'+
      '</div>'+
    '</div>'+
  '</div>';
}

function buildNotificationsSkeleton(){
  return '<div id="'+overlayId+'" data-page="notifications">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<div class="notif-skeleton-container">'+
      '<div class="notif-head">'+
        '<div class="notif-eyebrow"><div class="gh-dot" style="width:6px; height:6px; border-radius:50%; background:#22c55e;"></div><div class="gh-eyebrow-line sk" style="width:120px; height:11px;"></div></div>'+
        '<div class="gh-title sk" style="width:140px; height:26px;"></div>'+
        '<div class="notif-unread sk"></div>'+
      '</div>'+
      '<div class="notif-filter sk"></div>'+
      '<div class="card notif-list">'+
        '<div class="notif-row">'+
          '<div class="notif-avatar sk"></div>'+
          '<div class="notif-text"><div class="notif-line1 sk"></div><div class="notif-line2 sk"></div></div>'+
          '<div class="notif-time sk"></div>'+
        '</div>'+
        '<div class="notif-row">'+
          '<div class="notif-avatar sk"></div>'+
          '<div class="notif-text"><div class="notif-line1 sk"></div><div class="notif-line2 sk"></div></div>'+
          '<div class="notif-time sk"></div>'+
        '</div>'+
        '<div class="notif-row">'+
          '<div class="notif-avatar sk"></div>'+
          '<div class="notif-text"><div class="notif-line1 sk"></div><div class="notif-line2 sk"></div></div>'+
          '<div class="notif-time sk"></div>'+
        '</div>'+
        '<div class="notif-row">'+
          '<div class="notif-avatar sk"></div>'+
          '<div class="notif-text"><div class="notif-line1 sk"></div><div class="notif-line2 sk"></div></div>'+
          '<div class="notif-time sk"></div>'+
        '</div>'+
        '<div class="notif-row">'+
          '<div class="notif-avatar sk"></div>'+
          '<div class="notif-text"><div class="notif-line1 sk"></div><div class="notif-line2 sk"></div></div>'+
          '<div class="notif-time sk"></div>'+
        '</div>'+
      '</div>'+
      '<div class="notif-actions">'+
        '<div class="notif-btn sk"></div>'+
        '<div class="notif-btn sk"></div>'+
      '</div>'+
      '<div class="notif-btn-all sk"></div>'+
    '</div>'+
  '</div>';
}

function buildPostDetailSkeleton(){
  return '<div id="'+overlayId+'" data-page="post-detail">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<div class="post-detail-skeleton-container">'+
      '<div class="card post-card">'+
        '<div class="post-head">'+
          '<div class="post-avatar sk"></div>'+
          '<div class="post-meta">'+
            '<div class="post-name sk"></div>'+
            '<div class="post-time sk"></div>'+
          '</div>'+
          '<div class="post-kebab sk"></div>'+
        '</div>'+
        '<div class="post-text sk"></div>'+
        '<div class="post-media sk"></div>'+
        '<div class="post-actions">'+
          '<div class="action w1 sk"></div><div class="action w2 sk"></div>'+
          '<div class="action w3 sk"></div><div class="action w4 sk"></div>'+
        '</div>'+
        '<div class="comment-row">'+
          '<div class="comment-avatar sk"></div>'+
          '<div class="comment-input-wrap">'+
            '<div class="comment-input sk"></div>'+
            '<div class="comment-send sk"></div>'+
          '</div>'+
        '</div>'+
      '</div>'+
    '</div>'+
  '</div>';
}

function buildGroupDetailSkeleton(){
  return '<div id="'+overlayId+'" data-page="group-detail">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<div class="group-detail-skeleton-container">'+
      '<div class="card group-card">'+
        '<div class="group-top">'+
          '<div class="group-icon sk"></div>'+
          '<div class="group-info">'+
            '<div class="group-title-row"><div class="group-title sk"></div><div class="group-badge sk"></div></div>'+
            '<div class="group-desc sk"></div>'+
          '</div>'+
        '</div>'+
        '<div class="group-bottom"><div class="group-count sk"></div><div class="group-view sk"></div></div>'+
      '</div>'+
      '<div class="group-actions">'+
        '<div class="group-btn sk"></div>'+
        '<div class="group-btn sk"></div>'+
      '</div>'+
    '</div>'+
  '</div>';
}

function buildCourseDetailSkeleton(){
  return '<div id="'+overlayId+'" data-page="course-detail">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<div class="course-skeleton-container">'+
      '<div class="card course-header">'+
        '<div class="course-title sk"></div>'+
        '<div class="course-desc sk"></div>'+
        '<div class="course-desc-2 sk"></div>'+
      '</div>'+
      '<div class="card course-content">'+
        '<div class="content-title sk"></div>'+
        '<div class="content-block">'+
          '<div class="content-line sk"></div>'+
          '<div class="content-line sk"></div>'+
          '<div class="content-line-short sk"></div>'+
        '</div>'+
        '<div class="content-block">'+
          '<div class="content-line sk"></div>'+
          '<div class="content-line-short sk"></div>'+
        '</div>'+
      '</div>'+
      '<div class="card course-resources">'+
        '<div class="content-title sk"></div>'+
        '<div class="resource-item">'+
          '<div class="resource-icon sk"></div>'+
          '<div class="resource-name sk"></div>'+
        '</div>'+
        '<div class="resource-item">'+
          '<div class="resource-icon sk"></div>'+
          '<div class="resource-name sk"></div>'+
        '</div>'+
      '</div>'+
      '<div class="card course-progress">'+
        '<div class="progress-title sk"></div>'+
        '<div class="progress-bar sk"></div>'+
        '<div class="progress-text sk"></div>'+
      '</div>'+
    '</div>'+
  '</div>';
}

function buildMessagingListSkeleton(){
  return '<div id="'+overlayId+'" data-page="messaging-list">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<div class="messaging-list-skeleton-container">'+
      '<div class="card msg-list">'+
        '<div class="msg-row">'+
          '<div class="msg-avatar sk"></div>'+
          '<div class="msg-text"><div class="msg-line1 sk"></div><div class="msg-line2 sk"></div></div>'+
          '<div class="msg-time sk"></div>'+
        '</div>'+
        '<div class="msg-row">'+
          '<div class="msg-avatar sk"></div>'+
          '<div class="msg-text"><div class="msg-line1 sk"></div><div class="msg-line2 sk"></div></div>'+
          '<div class="msg-time sk"></div>'+
        '</div>'+
        '<div class="msg-row">'+
          '<div class="msg-avatar sk"></div>'+
          '<div class="msg-text"><div class="msg-line1 sk"></div><div class="msg-line2 sk"></div></div>'+
          '<div class="msg-time sk"></div>'+
        '</div>'+
        '<div class="msg-row">'+
          '<div class="msg-avatar sk"></div>'+
          '<div class="msg-text"><div class="msg-line1 sk"></div><div class="msg-line2 sk"></div></div>'+
          '<div class="msg-time sk"></div>'+
        '</div>'+
        '<div class="msg-row">'+
          '<div class="msg-avatar sk"></div>'+
          '<div class="msg-text"><div class="msg-line1 sk"></div><div class="msg-line2 sk"></div></div>'+
          '<div class="msg-time sk"></div>'+
        '</div>'+
      '</div>'+
    '</div>'+
  '</div>';
}

function buildMessagingDetailSkeleton(){
  return '<div id="'+overlayId+'" data-page="messaging-detail">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<div class="messaging-detail-skeleton-container">'+
      '<div class="msg-bubble-row">'+
        '<div class="msg-avatar sk"></div>'+
        '<div class="msg-bubble w70 sk"></div>'+
      '</div>'+
      '<div class="msg-bubble-row sent">'+
        '<div class="msg-bubble w60 sk"></div>'+
      '</div>'+
      '<div class="msg-bubble-row">'+
        '<div class="msg-avatar sk"></div>'+
        '<div class="msg-bubble w75 sk"></div>'+
      '</div>'+
      '<div class="msg-bubble-row sent">'+
        '<div class="msg-bubble w50 sk"></div>'+
      '</div>'+
      '<div class="msg-bubble-row">'+
        '<div class="msg-avatar sk"></div>'+
        '<div class="msg-bubble w65 sk"></div>'+
      '</div>'+
      '<div class="msg-input-area">'+
        '<div class="msg-input-avatar sk"></div>'+
        '<div class="msg-input sk"></div>'+
        '<div class="msg-send sk"></div>'+
      '</div>'+
    '</div>'+
  '</div>';
}

function buildSearchResultsSkeleton(){
  return '<div id="'+overlayId+'" data-page="search">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<div class="search-results-skeleton-container">'+
      '<div class="search-header">'+
        '<div class="search-title sk"></div>'+
      '</div>'+
      '<div class="feed-col">'+
        '<div class="card post-card">'+
          '<div class="post-head">'+
            '<div class="post-avatar sk"></div>'+
            '<div class="post-meta">'+
              '<div class="post-name sk"></div>'+
              '<div class="post-time sk"></div>'+
            '</div>'+
            '<div class="post-kebab sk"></div>'+
          '</div>'+
          '<div class="post-text sk"></div>'+
          '<div class="post-media sk"></div>'+
          '<div class="post-actions">'+
            '<div class="action w1 sk"></div><div class="action w2 sk"></div>'+
            '<div class="action w3 sk"></div><div class="action w4 sk"></div>'+
          '</div>'+
          '<div class="comment-row">'+
            '<div class="comment-avatar sk"></div>'+
            '<div class="comment-input-wrap">'+
              '<div class="comment-input sk"></div>'+
              '<div class="comment-send sk"></div>'+
            '</div>'+
          '</div>'+
        '</div>'+
        '<div class="card post-card">'+
          '<div class="post-head">'+
            '<div class="post-avatar sk"></div>'+
            '<div class="post-meta">'+
              '<div class="post-name sk"></div>'+
              '<div class="post-time sk"></div>'+
            '</div>'+
            '<div class="post-kebab sk"></div>'+
          '</div>'+
          '<div class="post-text sk"></div>'+
          '<div class="post-actions">'+
            '<div class="action w1 sk"></div><div class="action w2 sk"></div>'+
            '<div class="action w3 sk"></div><div class="action w4 sk"></div>'+
          '</div>'+
          '<div class="comment-row">'+
            '<div class="comment-avatar sk"></div>'+
            '<div class="comment-input-wrap">'+
              '<div class="comment-input sk"></div>'+
              '<div class="comment-send sk"></div>'+
            '</div>'+
          '</div>'+
        '</div>'+
      '</div>'+
    '</div>'+
  '</div>';
}

function injectCSS(){
  if(document.getElementById('skel-css-v3'))return;
  var s=document.createElement('style');
  s.id='skel-css-v3';
  s.textContent=
  '#'+overlayId+'{position:fixed;top:0;left:0;width:100vw;height:100vh;background:var(--bg,#f7f8fa);z-index:99999;overflow-y:auto;padding-bottom:80px;animation:skelFadeIn .3s ease;pointer-events:none}'+ '#'+overlayId+'.show{pointer-events:auto}'+
  '@keyframes skelFadeIn{from{opacity:0}to{opacity:1}}'+

  '.skel-offline-banner{position:sticky;top:0;z-index:100000;background:#ef4444;color:#fff;text-align:center;padding:8px 16px;font-size:13px;font-weight:600;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;display:flex;align-items:center;justify-content:center;gap:8px}'+
  '.skel-pulse{animation:skelPulse 1.5s infinite}'+
  '@keyframes skelPulse{0%,100%{opacity:.5}50%{opacity:1}}'+

  /* CSS Variables */
  ':root{--brand:#2f63eb;--brand-light:#eef3ff;--brand-mid:#4f7df0;--ink-accent:#1a1410;--ink:#1a1a1a;--muted:#6b7280;--border:#e8e9ec;--bg:#f7f8fa;--card:#ffffff;--sk-base:#e9eaee;--sk-shine:#f6f7f9;--danger:#dc2626;--radius:14px}'+
  '[data-theme="dark"]{--brand:#5b8dff;--brand-light:#1b2540;--brand-mid:#3f5fb0;--ink-accent:#f2f3f5;--ink:#f2f3f5;--muted:#9aa0ab;--border:#2a2d34;--bg:#15161a;--card:#1e2025;--sk-base:#2a2d34;--sk-shine:#363a42;--danger:#f87171}'+

  /* Shimmer */
  '.sk{background:linear-gradient(100deg,var(--sk-base) 30%,var(--sk-shine) 45%,var(--sk-base) 60%);background-size:250% 100%;animation:shimmer 1.5s ease-in-out infinite;border-radius:6px}'+
  '@keyframes shimmer{0%{background-position:120% 0}100%{background-position:-20% 0}}'+
  '@media (prefers-reduced-motion: reduce){.sk{animation:none;background:var(--sk-base)}}'+

  /* Card */
  '.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);box-shadow:0 1px 2px rgba(16,24,40,.04);transition:background .2s ease,border-color .2s ease}'+

  /* Container queries */
  '.home-skeleton-container,.profile-skeleton-container,.groups-skeleton-container,.notif-skeleton-container,.post-detail-skeleton-container,.group-detail-skeleton-container,.course-skeleton-container,.messaging-list-skeleton-container,.messaging-detail-skeleton-container,.search-results-skeleton-container{container-type:inline-size;width:100%;padding:24px}'+

  /* Home skeleton */
  '.search-row{display:flex;align-items:center;gap:12px;padding:14px 18px;margin-bottom:22px}'+
  '.search-avatar{width:34px;height:34px;border-radius:50%;flex-shrink:0}'+
  '.search-bar{flex:1;height:34px;border-radius:999px}'+
  '.explore-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}'+
  '.explore-head .et{width:160px;height:12px}'+
  '.explore-head .ev{width:60px;height:12px}'+
  '.explore-row{display:flex;gap:22px;overflow:hidden;margin-bottom:28px}'+
  '.explore-item{display:flex;flex-direction:column;align-items:center;gap:8px;flex-shrink:0}'+
  '.explore-circle{width:56px;height:56px;border-radius:50%}'+
  '.explore-label{width:48px;height:9px}'+

  /* Feed */
  '.feed-col{display:flex;flex-direction:column;gap:18px}'+
  '.post-card{padding:18px}'+
  '.post-head{display:flex;align-items:center;gap:12px;margin-bottom:14px}'+
  '.post-avatar{width:42px;height:42px;border-radius:50%;flex-shrink:0}'+
  '.post-meta{flex:1}'+
  '.post-name{width:140px;height:13px;margin-bottom:8px}'+
  '.post-time{width:90px;height:10px}'+
  '.post-kebab{width:18px;height:18px;border-radius:4px;flex-shrink:0}'+
  '.post-text{width:40%;height:12px;margin-bottom:14px}'+
  '.post-media{width:100%;height:220px;border-radius:10px;margin-bottom:14px}'+
  '.post-actions{display:flex;gap:22px;margin-bottom:14px}'+
  '.action{height:14px}'+
  '.action.w1{width:40px}.action.w2{width:34px}.action.w3{width:34px}.action.w4{width:50px}'+
  '.comment-row{display:flex;align-items:center;gap:10px;border-top:1px solid var(--border);padding-top:14px}'+
  '.comment-avatar{width:30px;height:30px;border-radius:50%;flex-shrink:0}'+
  '.comment-input-wrap{position:relative;flex:1}'+
  '.comment-input{height:36px;border-radius:999px}'+
  '.comment-send{position:absolute;right:8px;top:50%;transform:translateY(-50%);width:18px;height:18px;border-radius:50%}'+

  /* Profile */
  '.profile-grid{display:grid;grid-template-columns:300px 1fr;gap:24px}'+
  '@container (max-width: 820px){.profile-grid{grid-template-columns:1fr}}'+
  '.profile-card{overflow:hidden}'+
  '.cover{height:140px;border-radius:0}'+
  '.avatar-wrap{margin-top:-44px;display:flex;justify-content:center}'+
  '.avatar{width:88px;height:88px;border-radius:50%;border:4px solid var(--card)}'+
  '.profile-body{padding:0 20px 20px;text-align:center}'+
  '.badge-line{width:90px;height:20px;border-radius:999px;margin:10px auto 14px}'+
  '.name-line{width:60%;height:18px;margin:0 auto 8px}'+
  '.handle-line{width:35%;height:13px;margin:0 auto 16px}'+
  '.bio-line{width:80%;height:30px;border-radius:999px;margin:0 auto 18px}'+
  '.btn-line{height:42px;border-radius:999px;margin-bottom:10px;border:1px solid var(--border)}'+
  '.stats-row{display:flex;border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:16px 0;margin-top:10px}'+
  '.stat{flex:1;text-align:center}'+
  '.stat .num{width:34px;height:18px;margin:0 auto 8px}'+
  '.stat .lbl{width:50px;height:10px;margin:0 auto}'+
  '.side-card{padding:18px;margin-top:18px}'+
  '.side-title-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}'+
  '.side-title{width:55%;height:14px}'+
  '.side-hide{width:36px;height:11px}'+
  '.side-row{display:flex;justify-content:space-between;margin-bottom:12px}'+
  '.side-row .k{width:35%;height:12px}'+
  '.side-row .v{width:20%;height:12px}'+
  '.bar{height:8px;border-radius:999px;margin:10px 0 14px}'+
  '.para-line{height:11px;margin-bottom:8px}'+

  /* Groups */
  '.groups-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px;gap:12px}'+
  '.gh-eyebrow{display:flex;align-items:center;gap:6px;margin-bottom:10px}'+
  '.gh-dot{width:6px;height:6px;border-radius:50%;background:#22c55e}'+
  '.gh-eyebrow-line{width:120px;height:11px}'+
  '.gh-title{width:140px;height:26px}'+
  '.gh-btn{width:130px;height:40px;border-radius:999px;flex-shrink:0}'+
  '.groups-grid{display:grid;grid-template-columns:260px 1fr;gap:22px}'+
  '@container (max-width: 820px){.groups-grid{grid-template-columns:1fr}}'+
  '.your-groups{padding:18px;margin-bottom:18px}'+
  '.yg-label-row{display:flex;align-items:center;gap:8px;margin-bottom:18px}'+
  '.yg-icon-sm{width:14px;height:14px;border-radius:4px}'+
  '.yg-label{width:80px;height:11px}'+
  '.yg-empty{padding:18px 0;text-align:center}'+
  '.yg-icon{width:40px;height:40px;border-radius:50%;margin:0 auto 14px}'+
  '.yg-line{width:70%;height:11px;margin:0 auto}'+
  '.how-card{padding:18px}'+
  '.how-head{display:flex;align-items:center;gap:8px;margin-bottom:12px}'+
  '.how-icon{width:14px;height:14px;border-radius:4px}'+
  '.how-title{width:55%;height:12px}'+
  '.all-groups-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}'+
  '.ag-label{width:80px;height:13px}'+
  '.ag-count{width:70px;height:20px;border-radius:999px}'+
  '.group-list{display:flex;flex-direction:column;gap:14px}'+
  '.group-card{padding:18px}'+
  '.group-top{display:flex;align-items:flex-start;gap:14px;margin-bottom:14px}'+
  '.group-icon{width:46px;height:46px;border-radius:50%;flex-shrink:0}'+
  '.group-info{flex:1}'+
  '.group-title-row{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}'+
  '.group-title{width:200px;height:14px}'+
  '.group-badge{width:60px;height:18px;border-radius:999px}'+
  '.group-desc{width:80%;height:11px}'+
  '.group-bottom{display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--border);padding-top:12px}'+
  '.group-count{width:40px;height:11px}'+
  '.group-view{width:60px;height:11px}'+

  /* Notifications */
  '.notif-head{margin-bottom:18px}'+
  '.notif-eyebrow{display:flex;align-items:center;gap:6px;margin-bottom:10px}'+
  '.notif-unread{width:80px;height:22px;border-radius:999px;margin-top:10px}'+
  '.notif-filter{width:100%;max-width:260px;height:42px;border-radius:10px;margin-bottom:18px}'+
  '.notif-list .notif-row{display:flex;align-items:flex-start;gap:14px;padding:18px;border-bottom:1px solid var(--border)}'+
  '.notif-list .notif-row:last-child{border-bottom:none}'+
  '.notif-avatar{width:38px;height:38px;border-radius:50%;flex-shrink:0}'+
  '.notif-text{flex:1}'+
  '.notif-line1{width:120px;height:11px;margin-bottom:8px}'+
  '.notif-line2{width:80%;height:11px}'+
  '.notif-time{width:70px;height:10px;flex-shrink:0}'+
  '.notif-actions{display:flex;gap:12px;margin-top:18px}'+
  '.notif-btn{flex:1;height:38px;border-radius:999px}'+
  '.notif-btn-all{height:44px;border-radius:999px;margin-top:12px}'+

  /* Post Detail */
  '.post-detail-skeleton-container{container-name:post-detail}'+
  '.group-detail-skeleton-container{container-name:group-detail}'+
  '.group-actions{display:flex;gap:12px;margin-top:18px}'+
  '.group-btn{flex:1;height:38px;border-radius:999px}'+

  /* Course */
  '.course-header{padding:18px;margin-bottom:18px}'+
  '.course-title{width:200px;height:26px;margin-bottom:12px}'+
  '.course-desc{width:80%;height:11px;margin-bottom:8px}'+
  '.course-desc-2{width:70%;height:11px}'+
  '.course-content{padding:18px;margin-bottom:18px}'+
  '.content-title{width:120px;height:14px;margin-bottom:16px}'+
  '.content-block{margin-bottom:16px}'+
  '.content-line{width:100%;height:11px;margin-bottom:8px}'+
  '.content-line-short{width:90%;height:11px}'+
  '.course-resources{padding:18px;margin-bottom:18px}'+
  '.resource-item{display:flex;align-items:center;gap:12px;padding:12px;background:var(--bg);border-radius:8px;margin-bottom:12px}'+
  '.resource-icon{width:32px;height:32px;border-radius:50%;flex-shrink:0}'+
  '.resource-name{flex:1;height:11px}'+
  '.course-progress{padding:18px}'+
  '.progress-title{width:100px;height:14px;margin-bottom:12px}'+
  '.progress-bar{width:100%;height:8px;border-radius:999px;margin-bottom:8px}'+
  '.progress-text{width:40px;height:11px}'+

  /* Messaging */
  '.msg-list .msg-row{display:flex;align-items:flex-start;gap:14px;padding:18px;border-bottom:1px solid var(--border)}'+
  '.msg-list .msg-row:last-child{border-bottom:none}'+
  '.msg-avatar{width:38px;height:38px;border-radius:50%;flex-shrink:0}'+
  '.msg-text{flex:1}'+
  '.msg-line1{width:120px;height:11px;margin-bottom:8px}'+
  '.msg-line2{width:80%;height:11px}'+
  '.msg-time{width:70px;height:10px;flex-shrink:0}'+
  '.msg-bubble-row{display:flex;gap:12px;margin-bottom:16px}'+
  '.msg-bubble-row.sent{justify-content:flex-end}'+
  '.msg-avatar{width:32px;height:32px;border-radius:50%;flex-shrink:0}'+
  '.msg-bubble{height:40px;border-radius:12px}'+
  '.msg-bubble.w70{width:70%}.msg-bubble.w60{width:60%}.msg-bubble.w75{width:75%}.msg-bubble.w50{width:50%}.msg-bubble.w65{width:65%}'+
  '.msg-input-area{display:flex;gap:12px;padding:18px;border-top:1px solid var(--border);margin-top:18px}'+
  '.msg-input-avatar{width:32px;height:32px;border-radius:50%;flex-shrink:0}'+
  '.msg-input{flex:1;height:40px;border-radius:999px}'+
  '.msg-send{width:32px;height:32px;border-radius:50%;flex-shrink:0}'+

  /* Search */
  '.search-header{margin-bottom:18px}'+
  '.search-title{width:200px;height:26px}'+

  /* Mobile */
  '@media (max-width: 600px){.profile-skeleton-container{padding:16px}.profile-card{margin:-16px -16px 0;border-left:none;border-right:none;border-top:none;border-radius:0}}';

  document.head.appendChild(s);
}

async function show(){
  if(isShowing)return;
  var pageType=detectPageType();
  if(pageType==='messages'||pageType==='messaging-list'||pageType==='messaging-detail'){console.log('Messages page - skeleton skipped');return;}
  isShowing=true;
  console.log('Showing skeleton for:',pageType);
  injectCSS();
  var html=await buildHTML(pageType);
  document.body.insertAdjacentHTML('beforeend',html);
  var el=document.getElementById(overlayId);
  if(el){ el.style.pointerEvents='auto'; el.style.opacity='1'; }
}

function hide(){
  if(!isShowing)return;
  isShowing=false;
  var el=document.getElementById(overlayId);
  if(el){ el.style.pointerEvents='none'; el.style.opacity='0'; el.style.transition='opacity .3s'; setTimeout(function(){if(el.parentNode)el.parentNode.removeChild(el);},300); }
}

window.addEventListener('offline',function(){console.log('Offline detected');show();});
window.addEventListener('online',function(){console.log('Online detected');fetch('/static/images/favicon.ico',{method:'HEAD'}).then(function(r){if(r.ok)hide();});});

// Sync with navigation skeleton system
window.addEventListener('offline',function(){
  // Hide navigation skeleton if visible when going offline
  if(window.PwaniNetNavigationSkeleton){
    window.PwaniNetNavigationSkeleton.hideNavigationSkeleton();
  }
});

window.PwaniNetOfflineSkeleton={show:show,hide:hide};
})();
