/**
 * Facebook Apple Emojis Content Script
 * Converts Facebook custom emoji images into authentic Apple Color Emoji characters.
 */

(function () {
  'use strict';

  function replaceEmoji(img) {
    if (img.dataset.appleEmojiDone) return;
    img.dataset.appleEmojiDone = 'true';

    const alt = img.getAttribute('alt');
    if (!alt) return;

    const span = document.createElement('span');
    span.className = 'apple-emoji-text';
    span.textContent = alt;

    const heightAttr = img.getAttribute('height') || img.style.height || '';
    const h = parseInt(heightAttr, 10);

    if (h >= 28) {
      span.classList.add('large-emoji');
    } else {
      span.classList.add('inline-emoji');
    }

    // Hide original image and insert our authentic Apple emoji span
    img.style.display = 'none';
    if (img.parentNode) {
      img.parentNode.insertBefore(span, img.nextSibling);
    }
  }

  function processAllEmojis(root = document) {
    const images = root.querySelectorAll('img[src*="emoji.php"]');
    for (let i = 0; i < images.length; i++) {
      replaceEmoji(images[i]);
    }
  }

  // Initial pass
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => processAllEmojis());
  } else {
    processAllEmojis();
  }

  // MutationObserver for dynamic messages, chat, and feeds
  const observer = new MutationObserver((mutations) => {
    for (let m = 0; m < mutations.length; m++) {
      const mutation = mutations[m];
      if (mutation.type === 'childList') {
        for (let i = 0; i < mutation.addedNodes.length; i++) {
          const node = mutation.addedNodes[i];
          if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.tagName === 'IMG' && node.src && node.src.includes('emoji.php')) {
              replaceEmoji(node);
            } else {
              processAllEmojis(node);
            }
          }
        }
      } else if (mutation.type === 'attributes' && mutation.target.tagName === 'IMG') {
        const target = mutation.target;
        if (target.src && target.src.includes('emoji.php')) {
          replaceEmoji(target);
        }
      }
    }
  });

  observer.observe(document.documentElement || document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['src', 'alt']
  });

  // Re-check periodically for any lazy-loaded Messenger frames
  setInterval(() => {
    processAllEmojis();
  }, 1500);

  console.log('[Apple Emojis] Initialized for Facebook & Messenger.');
})();
