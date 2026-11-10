self.addEventListener("install",function(e){e.waitUntil(caches.open("td-v1").then(function(c){return c.addAll(["./","index.html","news.json","news.js","icon.svg"])}));self.skipWaiting()});
self.addEventListener("fetch",function(e){var r=e.request;if(r.method!=="GET"||new URL(r.url).origin!==location.origin)return;
e.respondWith(fetch(r).then(function(x){var cp=x.clone();caches.open("td-v1").then(function(c){c.put(r,cp)});return x}).catch(function(){return caches.match(r)}))});
