/**
 * PwaniNet Offline Skeleton Manager v2
 * Page-aware skeletons matching actual page layouts exactly
 * Messages page excluded (available offline)
 */
(function(){
'use strict';

var overlayId='offline-skeleton-overlay',isShowing=false;

function detectPageType(){
  var p=window.location.pathname;
  if(p.includes('/messages/'))return'messages';
  if(p.includes('/profile/')||p.match(/^\/users\/[^\/]+\/?$/))return'profile';
  if(p.includes('/groups/')&&!p.includes('/create'))return'groups';
  if(p.includes('/notifications/'))return'notifications';
  if(p==='/'||p==='/home/'||p.includes('/posts/'))return'home';
  return'home';
}

function buildHTML(type){
  if(type==='messages')return'';
  if(type==='profile')return buildProfileSkeleton();
  if(type==='groups')return buildGroupsSkeleton();
  if(type==='notifications')return buildNotificationsSkeleton();
  return buildHomeSkeleton();
}

function buildHomeSkeleton(){
  return '<div id="'+overlayId+'" data-page="home">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<header class="skel-search-header"><div class="skel-search-inner">'+
      '<div class="skel-avatar-42"></div>'+
      '<div class="skel-search-bar"></div>'+
    '</div></header>'+
    '<div class="skel-content-wrapper">'+
      '<div class="skel-groups-explore">'+
        '<div class="skel-groups-explore-header">'+
          '<div class="skel-line" style="width:130px;height:14px;border-radius:4px;"></div>'+
          '<div class="skel-line" style="width:60px;height:13px;border-radius:4px;"></div>'+
        '</div>'+
        '<div class="skel-groups-explore-list">'+
          '<div class="skel-group-explore-item"><div class="skel-circle-56"></div><div class="skel-line" style="width:50px;height:12px;margin-top:6px;"></div></div>'+
          '<div class="skel-group-explore-item"><div class="skel-circle-56"></div><div class="skel-line" style="width:50px;height:12px;margin-top:6px;"></div></div>'+
          '<div class="skel-group-explore-item"><div class="skel-circle-56"></div><div class="skel-line" style="width:50px;height:12px;margin-top:6px;"></div></div>'+
          '<div class="skel-group-explore-item"><div class="skel-circle-56"></div><div class="skel-line" style="width:50px;height:12px;margin-top:6px;"></div></div>'+
          '<div class="skel-group-explore-item"><div class="skel-circle-56"></div><div class="skel-line" style="width:50px;height:12px;margin-top:6px;"></div></div>'+
        '</div>'+
      '</div>'+
      buildPostCardSkeleton()+buildPostCardSkeleton()+buildPostCardSkeleton()+
    '</div></div>';
}

function buildPostCardSkeleton(){
  return '<div class="skel-post-card">'+
    '<div class="skel-post-header">'+
      '<div class="skel-avatar-48"></div>'+
      '<div class="skel-post-meta">'+
        '<div class="skel-line" style="width:120px;height:14px;margin-bottom:6px;"></div>'+
        '<div class="skel-line" style="width:80px;height:11px;"></div>'+
      '</div>'+
      '<div class="skel-menu-dot"></div>'+
    '</div>'+
    '<div class="skel-post-body">'+
      '<div class="skel-line" style="width:100%;height:14px;margin-bottom:8px;"></div>'+
      '<div class="skel-line" style="width:100%;height:14px;margin-bottom:8px;"></div>'+
      '<div class="skel-line" style="width:60%;height:14px;"></div>'+
    '</div>'+
    '<div class="skel-post-media"></div>'+
    '<div class="skel-post-actions">'+
      '<div class="skel-line" style="width:56px;height:16px;"></div>'+
      '<div class="skel-line" style="width:56px;height:16px;"></div>'+
      '<div class="skel-line" style="width:56px;height:16px;"></div>'+
      '<div class="skel-line" style="width:56px;height:16px;"></div>'+
    '</div>'+
    '<div class="skel-post-comment">'+
      '<div class="skel-avatar-32"></div>'+
      '<div class="skel-line" style="flex-grow:1;height:36px;border-radius:18px;"></div>'+
    '</div></div>';
}

function buildProfileSkeleton(){
  return '<div id="'+overlayId+'" data-page="profile">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<div class="skel-content-wrapper">'+
      '<div class="skel-profile-card">'+
        '<div class="skel-cover"></div>'+
        '<div class="skel-avatar-120"></div>'+
        '<div class="skel-profile-info">'+
          '<div class="skel-line" style="width:160px;height:22px;margin:0 auto 6px;"></div>'+
          '<div class="skel-line" style="width:100px;height:14px;margin:0 auto 16px;"></div>'+
          '<div class="skel-profile-bio"></div>'+
          '<div style="display:flex;justify-content:center;gap:8px;margin-top:12px;">'+
            '<div class="skel-btn-pill"></div><div class="skel-btn-pill"></div>'+
          '</div>'+
        '</div>'+
        '<div class="skel-profile-stats">'+
          '<div class="skel-stat-item"><div class="skel-line" style="width:30px;height:18px;margin:0 auto 4px;"></div><div class="skel-line" style="width:50px;height:10px;margin:0 auto;"></div></div>'+
          '<div class="skel-stat-item"><div class="skel-line" style="width:30px;height:18px;margin:0 auto 4px;"></div><div class="skel-line" style="width:50px;height:10px;margin:0 auto;"></div></div>'+
          '<div class="skel-stat-item"><div class="skel-line" style="width:30px;height:18px;margin:0 auto 4px;"></div><div class="skel-line" style="width:50px;height:10px;margin:0 auto;"></div></div>'+
        '</div>'+
      '</div>'+
      '<div class="skel-profile-tabs"><div class="skel-tab-active"></div><div class="skel-tab"></div><div class="skel-tab"></div></div>'+
      buildPostCardSkeleton()+buildPostCardSkeleton()+
    '</div></div>';
}

function buildGroupsSkeleton(){
  var cards='';
  for(var i=0;i<6;i++){
    cards+='<div class="skel-group-card"><div class="skel-circle-56" style="margin:0 auto 8px;"></div>'+
      '<div class="skel-line" style="width:80px;height:14px;margin:0 auto 6px;"></div>'+
      '<div class="skel-line" style="width:60px;height:10px;margin:0 auto 12px;"></div>'+
      '<div class="skel-btn-sm"></div></div>';
  }
  return '<div id="'+overlayId+'" data-page="groups">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<div class="skel-content-wrapper">'+
      '<div class="skel-groups-page-header"><div class="skel-line" style="width:140px;height:24px;"></div><div class="skel-btn-sm"></div></div>'+
      '<div class="skel-groups-grid">'+cards+'</div>'+
    '</div></div>';
}

function buildNotificationsSkeleton(){
  var items='';
  for(var j=0;j<5;j++){
    items+='<div class="skel-notif-item"><div class="skel-avatar-42"></div>'+
      '<div style="flex-grow:1;"><div class="skel-line" style="width:85%;height:14px;margin-bottom:6px;"></div>'+
      '<div class="skel-line" style="width:40%;height:10px;"></div></div>'+
      '<div class="skel-notif-dot"></div></div>';
  }
  return '<div id="'+overlayId+'" data-page="notifications">'+
    '<div class="skel-offline-banner"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>'+
    '<div class="skel-content-wrapper">'+
      '<div class="skel-notif-page-header"><div class="skel-line" style="width:130px;height:24px;"></div><div class="skel-filter-btn"></div></div>'+
      '<div class="skel-notif-list">'+items+'</div>'+
    '</div></div>';
}

function injectCSS(){
  if(document.getElementById('skel-css-v2'))return;
  var s=document.createElement('style');
  s.id='skel-css-v2';
  s.textContent=
  '#'+overlayId+'{position:fixed;top:0;left:0;width:100vw;height:100vh;background:var(--background,#f8fafc);z-index:99999;overflow-y:auto;padding-bottom:80px;animation:skelFadeIn .3s ease}'+
  '@keyframes skelFadeIn{from{opacity:0}to{opacity:1}}'+

  '.skel-offline-banner{position:sticky;top:0;z-index:100000;background:#ef4444;color:#fff;text-align:center;padding:8px 16px;font-size:13px;font-weight:600;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;display:flex;align-items:center;justify-content:center;gap:8px}'+
  '.skel-pulse{animation:skelPulse 1.5s infinite}'+
  '@keyframes skelPulse{0%,100%{opacity:.5}50%{opacity:1}}'+

  /* Shimmer */
  '.skel-avatar-42::after,.skel-avatar-48::after,.skel-avatar-32::after,.skel-avatar-120::after,.skel-circle-56::after,.skel-line::after,.skel-menu-dot::after,.skel-post-media::after,.skel-cover::after,.skel-profile-bio::after,.skel-btn-pill::after,.skel-btn-sm::after,.skel-filter-btn::after,.skel-notif-dot::after,.skel-search-bar::after{content:"";position:absolute;top:0;left:0;width:100%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.4),transparent);animation:skelShimmer 1.5s infinite}'+
  '[data-theme="dark"] .skel-avatar-42::after,[data-theme="dark"] .skel-avatar-48::after,[data-theme="dark"] .skel-avatar-32::after,[data-theme="dark"] .skel-avatar-120::after,[data-theme="dark"] .skel-circle-56::after,[data-theme="dark"] .skel-line::after,[data-theme="dark"] .skel-menu-dot::after,[data-theme="dark"] .skel-post-media::after,[data-theme="dark"] .skel-cover::after,[data-theme="dark"] .skel-profile-bio::after,[data-theme="dark"] .skel-btn-pill::after,[data-theme="dark"] .skel-btn-sm::after,[data-theme="dark"] .skel-filter-btn::after,[data-theme="dark"] .skel-notif-dot::after,[data-theme="dark"] .skel-search-bar::after{background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent)}'+
  '@keyframes skelShimmer{0%{transform:translateX(-100%)}100%{transform:translateX(100%)}}'+

  /* HOME: Search header */
  '.skel-search-header{position:sticky;top:0;z-index:100;background:var(--card-bg,#fff);border-bottom:1px solid var(--border,#e2e8f0);padding:12px 16px 10px}'+
  '.skel-search-inner{max-width:640px;margin:0 auto;display:flex;align-items:center;gap:12px}'+
  '.skel-avatar-42{width:42px;height:42px;border-radius:50%;background:var(--border,#e2e8f0);flex-shrink:0;position:relative;overflow:hidden}'+
  '.skel-search-bar{flex-grow:1;height:42px;border-radius:21px;background:var(--border,#e2e8f0);position:relative;overflow:hidden}'+

  /* Content wrapper */
  '.skel-content-wrapper{max-width:640px;margin:0 auto;padding:20px 16px 80px}'+
  '@media(max-width:767px){.skel-content-wrapper{max-width:100%!important;padding:20px 0 80px}}'+

  /* Groups explore */
  '.skel-groups-explore{margin-bottom:24px}'+
  '.skel-groups-explore-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}'+
  '.skel-groups-explore-list{display:flex;gap:16px;overflow-x:auto;padding-bottom:4px;scrollbar-width:none}'+
  '.skel-groups-explore-list::-webkit-scrollbar{display:none}'+
  '.skel-group-explore-item{flex-shrink:0;display:flex;flex-direction:column;align-items:center;width:70px}'+
  '.skel-circle-56{width:56px;height:56px;border-radius:50%;background:var(--border,#e2e8f0);box-shadow:0 2px 8px rgba(0,0,0,.1);position:relative;overflow:hidden}'+

  /* Post card */
  '.skel-post-card{background:var(--card-bg,#fff);border-radius:12px;margin-bottom:8px;overflow:hidden;border:1px solid var(--border,#e2e8f0);animation:skelCardIn .3s ease forwards}'+
  '.skel-post-card:nth-child(3){animation-delay:.1s}.skel-post-card:nth-child(4){animation-delay:.2s}.skel-post-card:nth-child(5){animation-delay:.3s}'+
  '@keyframes skelCardIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}'+
  '.skel-post-header{display:flex;align-items:center;padding:12px;gap:10px}'+
  '.skel-avatar-48{width:48px;height:48px;border-radius:50%;background:var(--border,#e2e8f0);flex-shrink:0;position:relative;overflow:hidden}'+
  '.skel-post-meta{flex-grow:1}'+
  '.skel-menu-dot{width:28px;height:28px;border-radius:4px;background:var(--border,#e2e8f0);flex-shrink:0;position:relative;overflow:hidden}'+
  '.skel-post-body{padding:0 12px 12px}'+
  '.skel-post-media{width:100%;height:250px;background:var(--border,#e2e8f0);position:relative;overflow:hidden}'+
  '.skel-post-actions{display:flex;gap:24px;padding:8px 12px;border-top:1px solid var(--border,#e2e8f0)}'+
  '.skel-post-comment{display:flex;align-items:center;gap:8px;padding:8px 12px 12px;border-top:1px solid var(--border,#e2e8f0)}'+
  '.skel-avatar-32{width:32px;height:32px;border-radius:50%;background:var(--border,#e2e8f0);flex-shrink:0;position:relative;overflow:hidden}'+
  '.skel-line{background:var(--border,#e2e8f0);border-radius:4px;position:relative;overflow:hidden}'+

  /* PROFILE */
  '.skel-profile-card{background:var(--card-bg,#fff);border-radius:12px;margin-bottom:8px;overflow:hidden;border:1px solid var(--border,#e2e8f0)}'+
  '.skel-cover{width:100%;height:160px;background:linear-gradient(135deg,#e2e8f0,#cbd5e1);position:relative;overflow:hidden}'+
  '.skel-avatar-120{width:120px;height:120px;border-radius:50%;background:var(--border,#e2e8f0);border:4px solid var(--card-bg,#fff);box-shadow:0 4px 12px rgba(0,0,0,.15);margin:-40px auto 10px;position:relative;overflow:hidden;z-index:1}'+
  '.skel-profile-info{text-align:center;padding:0 16px 16px}'+
  '.skel-profile-bio{width:80%;height:40px;margin:0 auto;background:var(--border,#e2e8f0);border-radius:8px;position:relative;overflow:hidden}'+
  '.skel-btn-pill{width:120px;height:36px;border-radius:18px;background:var(--border,#e2e8f0);position:relative;overflow:hidden}'+
  '.skel-profile-stats{display:flex;border-top:1px solid var(--border,#e2e8f0);padding:12px 0}'+
  '.skel-stat-item{flex:1;text-align:center;border-right:1px solid var(--border,#e2e8f0)}.skel-stat-item:last-child{border-right:none}'+
  '.skel-profile-tabs{display:flex;gap:0;margin-bottom:8px;border-bottom:2px solid var(--border,#e2e8f0);padding:0 16px}'+
  '.skel-tab-active{width:80px;height:40px;border-bottom:3px solid var(--primary,#2563eb);margin-right:16px}'+
  '.skel-tab{width:80px;height:40px;margin-right:16px}'+

  /* GROUPS */
  '.skel-groups-page-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}'+
  '.skel-groups-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px}'+
  '.skel-group-card{background:var(--card-bg,#fff);border-radius:12px;padding:16px;text-align:center;border:1px solid var(--border,#e2e8f0)}'+
  '.skel-btn-sm{width:80px;height:28px;border-radius:14px;background:var(--border,#e2e8f0);margin:0 auto;position:relative;overflow:hidden}'+

  /* NOTIFICATIONS */
  '.skel-notif-page-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}'+
  '.skel-filter-btn{width:100px;height:32px;border-radius:16px;background:var(--border,#e2e8f0);position:relative;overflow:hidden}'+
  '.skel-notif-list{display:flex;flex-direction:column;gap:8px}'+
  '.skel-notif-item{display:flex;align-items:center;gap:12px;padding:12px;background:var(--card-bg,#fff);border-radius:12px;border:1px solid var(--border,#e2e8f0)}'+
  '.skel-notif-dot{width:10px;height:10px;border-radius:50%;background:var(--primary,#2563eb);flex-shrink:0}'+

  /* Mobile */
  '@media(max-width:767px){.skel-post-media{height:200px}.skel-cover{height:120px}.skel-avatar-120{width:96px;height:96px;margin:-32px auto 8px}.skel-groups-grid{grid-template-columns:repeat(auto-fill,minmax(140px,1fr))}}';

  document.head.appendChild(s);
}

function show(){
  if(isShowing)return;
  var pageType=detectPageType();
  if(pageType==='messages'){console.log('Messages page - skeleton skipped');return;}
  isShowing=true;
  console.log('Showing skeleton for:',pageType);
  injectCSS();
  document.body.insertAdjacentHTML('beforeend',buildHTML(pageType));
}

function hide(){
  if(!isShowing)return;
  isShowing=false;
  var el=document.getElementById(overlayId);
  if(el){el.style.opacity='0';el.style.transition='opacity .3s';setTimeout(function(){if(el.parentNode)el.parentNode.removeChild(el);},300);}
}

window.addEventListener('offline',function(){console.log('Offline detected');show();});
window.addEventListener('online',function(){console.log('Online detected');fetch('/static/images/favicon.ico',{method:'HEAD'}).then(function(r){if(r.ok)hide();});});
window.PwaniNetOfflineSkeleton={show:show,hide:hide};
})();
