# Neo-Bloggy Improvement Plan

Comprehensive plan to improve the website's performance, accessibility, security, and database optimization.

## Current Scores (as of April 2026)
- Performance: 84/100 (Good) - *Improved from 63/100*
- Accessibility: 98/100 (Excellent) - *Improved from 94/100*
- Best Practices: 96/100 (Excellent) - *Recovered from temporary decrease to 88/100*
- SEO: 100/100 (Excellent) - *Maintained*

## 1. Performance Improvements

### Critical Issues (High Priority)

#### 1.1 Optimize Render-Blocking Resources ⏳ PARTIALLY COMPLETED
**Issue**: Multiple CSS and JS files blocking initial page render (estimated 2,820ms savings)

**Recommendations**:
- Inline critical CSS for above-the-fold content ✅ COMPLETED
- Defer non-critical CSS and JavaScript ⏳ PARTIALLY - Custom CSS loaded synchronously, not using preload+onload pattern
- Use `preload` for critical resources ✅ COMPLETED (jumbotron images preloaded)
- Add `async` or `defer` attributes to JavaScript files ✅ COMPLETED

**Files modified**:
- `templates/header.html` ✅
- `templates/footer.html` ✅

**Changes made**:
- Added preconnect hints for third-party domains ✅
- Added critical CSS inlined in `<style>` tag with nonce attribute ✅
- Added font optimization with `display=swap` and fallback fonts with `size-adjust` ✅
- Added `fetchpriority="high"` for important images ✅
- Added `defer` attributes to JavaScript files in footer ✅

**Current state (header.html)**:
- Bootstrap and Font Awesome CSS loaded **synchronously** via `<link rel="stylesheet">` (not the preload+onload pattern)
- Custom CSS (`style.css`, `table_style.css`, `pygments.css`) loaded synchronously
- Highlight.js stylesheet loaded synchronously
- Highlight.js script loaded with `async` attribute
- Critical CSS properly inlined above-the-fold
- Font preloading with `display=swap` implemented
- Jumbotron background images preloaded conditionally

**Note**: The preload+onload pattern described in the original plan was not implemented. CSS resources use standard synchronous loading to prevent FOUC (Flash of Unstyled Content), which is a valid trade-off decision.

**Still pending**:
- Consider preload+onload pattern for non-critical CSS if render-blocking becomes an issue
- Evaluate if current synchronous CSS loading causes measurable performance impact

#### 1.2 Image Optimization ⏳ PARTIALLY COMPLETED
**Issue**: Large images with significant potential savings (472KB)
- Image at `/gridfs/68e375f….webp`: 447.1 KiB (could save 432.9 KiB)
- Image at `/gridfs/68fef65….webp`: 42.3 KiB (could save 38.7 KiB)

**Recommendations**:
- Implement responsive images with `srcset` and `sizes` attributes
- Add explicit width and height attributes to prevent layout shifts
- Add image compression with appropriate quality settings
- Consider lazy loading for below-the-fold images

**Files modified**:
- `templates/index.html` ✅
- `templates/header.html` ✅

**Changes made**:
- Added explicit width/height attributes to images to prevent layout shifts
- Added `loading="lazy"` attribute to non-critical images
- Added `fetchpriority="high"` to critical images
- Added preloading for jumbotron images with conditional loading based on page

**Still pending**:
- Implement proper responsive images with `srcset` and `sizes` attributes
- Add server-side image resizing to generate multiple image sizes
- Add image compression and optimization functions in app.py
- Implement a Jinja2 template filter for responsive images

#### 1.3 Remove Unused CSS and JavaScript ⏳ PENDING
**Issue**: Unused CSS and JavaScript in CDN bundles

**Recommendations**:
- Audit and remove unused Bootstrap components
- Remove unused Font Awesome icons
- Optimize the EasyMDE editor (loaded per-page, not globally)

**Current state**:
- EasyMDE is lazy-loaded only on `post.html` and `create_post.html` pages (good practice)
- Bootstrap and Font Awesome loaded as full CDN bundles
- No custom CSS/JS bundling or tree-shaking implemented

**Files to consider**:
- `templates/header.html` - CDN resource loading
- `templates/footer.html` - Script loading

**Note**: Removing unused CSS/JS from CDN bundles would require either:
1. Using custom-built minimal versions of Bootstrap/Font Awesome
2. Implementing a build step to create optimized bundles
3. Accepting the CDN bundle size as a trade-off for CDN caching benefits

### Medium Priority Issues

#### 1.4 Implement Font Optimization ✅ COMPLETED
**Issue**: Font loading delays (110ms savings possible)

**Recommendations**:
- Add `font-display: swap` to Google Fonts and FontAwesome
- Preload critical fonts

**Files modified**:
- `templates/header.html` ✅

**Changes made**:
- Updated font import to include `display=swap` parameter
- Added preconnect hints for font domains
- Added preload for font stylesheet

#### 1.5 Preconnect to Third-Party Origins ✅ COMPLETED
**Issue**: Missing preconnect hints for important domains

**Recommendations**:
- Add `preconnect` hints for important third-party domains:
  - `use.fontawesome.com`
  - `fonts.googleapis.com`
  - `cdn.jsdelivr.net`

**Files modified**:
- `templates/header.html` ✅

**Changes made**:
- Added preconnect hints for CDN domains

## 2. Accessibility Improvements

### Critical Issues (High Priority)

#### 2.1 Fix Unnamed Links ✅ COMPLETED
**Issue**: Social sharing links without discernible names

**Recommendations**:
- Add proper `aria-label` to social sharing icons
- Ensure all interactive elements have accessible names

**Files modified**:
- `templates/footer.html` ✅

**Changes made**:
- Added `aria-label` attributes to all social sharing links
- Updated Twitter icon to X icon with proper aria-label

#### 2.2 Fix Heading Hierarchy ✅ COMPLETED
**Issue**: Heading elements not in sequential order

**Recommendations**:
- Ensure proper heading order (h1 → h2 → h3 → h4 → h5)
- Fix h5 elements that should be other heading levels

**Files modified**:
- `templates/index.html` ✅

**Changes made**:
- Changed h5 elements to h3 for proper heading hierarchy

## 3. Security Improvements

### Critical Issues (High Priority)

#### 3.1 Implement Security Headers ⏳ MOSTLY COMPLETED
**Issue**: Missing critical security headers

**Recommendations**:
- Add Content Security Policy (CSP) header ⏳ Implemented but nonce not enforced
- Implement HSTS header with appropriate max-age ✅ COMPLETED
- Add Cross-Origin-Opener-Policy (COOP) header ✅ COMPLETED
- Implement X-Frame-Options or CSP frame-ancestors directive ✅ COMPLETED

**Files modified**:
- `neo_bloggy/middleware/__init__.py` (in `after_request` function) ✅

**Changes made**:
- Added X-Content-Type-Options, X-Frame-Options, X-XSS-Protection ✅
- Added Content Security Policy header ✅
- Added Strict-Transport-Security (HSTS) header ✅
- Added Cross-Origin-Opener-Policy header ✅
- Added Referrer-Policy header ✅ (not in original plan)
- Implemented CSP nonce generation system ✅

**Current CSP Implementation**:
The middleware uses a policy with trusted CDN allowlists:
- `default-src 'self'` - Restrictive default policy
- `script-src 'self' 'unsafe-inline' <trusted CDNs>` - Allows trusted CDN scripts
- `style-src 'self' 'unsafe-inline' <trusted CDNs>` - Allows trusted CDN styles
- `img-src 'self' data: blob: https:` - Allows images from multiple sources
- `font-src 'self' <trusted CDNs>` - Allows fonts from CDNs
- `connect-src 'self' <analytics endpoints>` - Allows analytics connections
- `frame-ancestors 'none'` - Prevents embedding in frames
- `object-src 'none'` - Prevents plugin content
- `base-uri 'self'` - Restricts base element
- `form-action 'self'` - Restricts form submissions

**⚠️ Known Issue - CSP Nonce Not Enforced**:
The `_build_csp_policy()` function in `middleware/__init__.py` checks for `"{nonce}"` placeholders in directive values, but **none of the `CSP_DIRECTIVES` values contain `"{nonce}"`**. This means:
- The nonce is generated and available to templates via `csp_nonce`
- Templates use `nonce="{{ csp_nonce }}"` on inline scripts/styles
- However, the CSP header does **not** include `'nonce-<value>'` in `script-src` or `style-src`
- Inline scripts work because `'unsafe-inline'` is still permitted
- The nonce attributes in templates provide no actual CSP enforcement benefit

**To fix this**, either:
1. Add `'{nonce}'` to `script-src` and `style-src` directives and update `_build_csp_policy` to replace it, OR
2. Remove nonce attributes from templates if `'unsafe-inline'` is intentionally kept

## 4. Implementation Steps

### Step 1: Performance Optimizations ⏳ PARTIALLY COMPLETED

#### 4.1 Update `templates/header.html` ⏳ PARTIALLY COMPLETED
1. Add preconnect hints for third-party domains: ✅ COMPLETED
```html
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="preconnect" href="https://use.fontawesome.com">
<link rel="preconnect" href="https://fonts.googleapis.com">
```

2. CSS loading: ⚠️ Uses synchronous `<link rel="stylesheet">` (not preload+onload)
```html
<!-- Current implementation: synchronous loading to prevent FOUC -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="https://use.fontawesome.com/releases/v6.5.1/css/all.css">

<!-- Custom CSS loaded synchronously -->
<link href="{{ url_for('static', filename='css/style.css')}}" rel="stylesheet">
<link href="{{ url_for('static', filename='css/table_style.css')}}" rel="stylesheet">
<link href="{{ url_for('static', filename='css/pygments.css', v='1.1')}}" rel="stylesheet">

<!-- Highlight.js stylesheet -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/default.min.css">

<!-- Google Fonts with display=swap -->
<link rel="preload" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:...&display=swap" as="style">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:...&display=swap" rel="stylesheet">
```

3. Critical CSS inlining: ✅ COMPLETED
- Large `<style nonce="{{ csp_nonce }}">` block with above-fold styles
- Font fallback definitions with `size-adjust`, `ascent-override` for CLS reduction

4. Jumbotron image preloading: ✅ COMPLETED
- Conditional preloading based on `request.endpoint`

#### 4.2 Update `templates/footer.html` ✅ COMPLETED
1. Optimize JavaScript loading by adding async/defer attributes: ✅ COMPLETED
```html
<script src="https://cdn.jsdelivr.net/npm/cash-dom@8.1.5/dist/cash.min.js" integrity="sha256-mgRBiO/bYlxeBNEiBpjAmZJ/8Wv7Q0w3zX8E3V7hrh8=" crossorigin="anonymous" defer></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous" defer></script>
<script src="https://cdn.jsdelivr.net/npm/easymde@2.18.0/dist/easymde.min.js" defer></script>
<script src="{{ url_for('static', filename='js/script.js')}}" defer></script>
```

2. Add proper aria-labels to social links: ✅ COMPLETED
```html
<ul class="list-inline text-center">
   <li class="list-inline-item">
      {% if post %}
      <a href="https://x.com/intent/post?url={{ request.url }}&text={{ post.title }}" target="_blank" rel="noopener noreferrer" aria-label="Share on X">
      {% else %}
      <a href="https://x.com/intent/post?url={{ url_for('posts.get_all_posts', _external=True) }}&text=Check out Neo Bloggy!" target="_blank" rel="noopener noreferrer" aria-label="Share Neo Bloggy on X">
      {% endif %}
      <span class="fa-stack fa-lg">
      <i class="fas fa-circle fa-stack-2x"></i>
      <i class="fab fa-x-twitter fa-stack-1x fa-inverse"></i>
      </span>
      </a>
   </li>
   <li class="list-inline-item">
      {% if post %}
      <a href="https://www.facebook.com/sharer/sharer.php?u={{ request.url }}" target="_blank" rel="noopener noreferrer" aria-label="Share on Facebook">
      {% else %}
      <a href="https://www.facebook.com/sharer/sharer.php?u={{ url_for('posts.get_all_posts', _external=True) }}" target="_blank" rel="noopener noreferrer" aria-label="Share Neo Bloggy on Facebook">
      {% endif %}
      <span class="fa-stack fa-lg">
      <i class="fas fa-circle fa-stack-2x"></i>
      <i class="fab fa-facebook-f fa-stack-1x fa-inverse"></i>
      </span>
      </a>
   </li>
   <li class="list-inline-item">
      <a href="https://github.com/cwt/neo-bloggy" target="_blank" rel="noopener noreferrer" aria-label="View on GitHub">
      <span class="fa-stack fa-lg">
      <i class="fas fa-circle fa-stack-2x"></i>
      <i class="fab fa-github fa-stack-1x fa-inverse"></i>
      </span>
      </a>
   </li>
</ul>
```

### Step 2: Update `templates/index.html` ✅ COMPLETED

1. Add explicit width/height attributes to images to prevent layout shifts: ✅ COMPLETED
```html
<div class="col-md-4">
   {% if loop.index0 == 0 %}
   <!-- First image should have high fetchpriority for LCP optimization -->
   <img src="{{ post.img_url }}" class="card-img" alt="{{ post.title }}" width="362" height="241" fetchpriority="high">
   {% else %}
   <img src="{{ post.img_url }}" class="card-img" alt="{{ post.title }}" width="362" height="241" loading="lazy">
   {% endif %}
</div>
```

2. Fix heading hierarchy (use h3 instead of h5 for post titles): ✅ COMPLETED
```html
<a href="{{ url_for('posts.show_post', post_id=post._id) }}">
   <h3 class="card-title">{{post.title}}</h3>
   <p class="card-text">{{ post.subtitle }}</p>
</a>
```

### Step 3: Modular Package Implementation ✅ COMPLETED

#### 3.1 Add security headers in `neo_bloggy/middleware/__init__.py` ✅ COMPLETED

**Current Implementation**:
```python
@staticmethod
def after_request(response):
    """Process HTML responses for minification and clean up expired cache."""
    # Clean up expired cache entries periodically (roughly every minute)
    if CACHE_ENABLED and int(time.time()) % 60 == 0:
        clear_expired_cache()

    # Add security headers
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value

    # Remove any previously set CSP headers to avoid conflicts
    response.headers.pop("Content-Security-Policy", None)
    response.headers.pop("Content-Security-Policy-Report-Only", None)

    # Add Content Security Policy with nonce-based protection
    csp_nonce = get_csp_nonce()
    response.headers["Content-Security-Policy"] = _build_csp_policy(csp_nonce)

    # Update session with current user info
    user = get_current_user()
    if user:
        session["user"] = user["name"]

    return response
```

**CSP Directives** (defined in `CSP_DIRECTIVES` dict):
- `default-src: 'self'`
- `script-src: 'self' 'unsafe-inline' <trusted CDNs>`
- `style-src: 'self' 'unsafe-inline' <trusted CDNs>`
- `img-src: 'self' data: blob: https:`
- `font-src: 'self' <trusted CDNs>`
- `connect-src: 'self' <analytics endpoints>`
- `frame-ancestors: 'none'`
- `object-src: 'none'`
- `base-uri: 'self'`
- `form-action: 'self'`

#### 3.2 Add nonce generation functions in `neo_bloggy/auth/__init__.py` ✅ COMPLETED
```python
def generate_nonce():
    """Generate a unique nonce for CSP."""
    import secrets
    return secrets.token_urlsafe(16)

def get_csp_nonce():
    """Get or create a CSP nonce for the current request."""
    if not hasattr(g, "csp_nonce"):
        g.csp_nonce = generate_nonce()
    return g.csp_nonce
```

#### 3.3 Update context processor in `neo_bloggy/__init__.py` ✅ COMPLETED
```python
@app.context_processor
def inject_site_details():
    """Inject site details into all templates."""
    from neo_bloggy.auth import (
        get_current_user, get_csp_nonce, get_absolute_url, get_canonical_url
    )
    user = get_current_user()
    if user:
        session["user"] = user["name"]

    return {
        "site_title": config.get("app", {}).get("site_title", "Neo Bloggy"),
        "site_author": config.get("app", {}).get("site_author", "Neo Bloggy"),
        "site_description": config.get("app", {}).get("site_description", "Blogging Ireland; journalism"),
        "user": user,
        "csp_nonce": get_csp_nonce(),
        "get_absolute_url": get_absolute_url,
        "get_canonical_url": get_canonical_url,
    }
```

#### 3.4 Image optimization functions ✅ COMPLETED (Basic)

**Implemented in `neo_bloggy/utils/__init__.py`**:
- `allowed_file()` - Validates allowed image extensions (png, jpg, jpeg, gif, webp)
- `validate_image_content()` - Validates uploaded files are actual images using PIL
- `get_content_type_from_file_extension()` - Maps file extensions to content types
- `get_file_extension_from_content_type()` - Maps content types to file extensions
- `markdown_to_html()` - Converts markdown with CSS sanitization via bleach
- `minify_html()` - HTML minification for responses
- Input validators: `UserValidator`, `PostValidator`, `InputValidator`

**Features**:
- Image validation using PIL
- Secure file upload handling
- HTML minification in middleware

**Not implemented** (despite plan mentioning WebP conversion):
- WebP conversion function for uploaded images

#### 3.5 Add a Jinja2 template filter for responsive images in `neo_bloggy/utils/template_filters.py` ⏳ PENDING

**Current template filters implemented** (in `neo_bloggy/utils/template_filters.py`):
- `register_template_filters(app)` - Registers all filters with the Flask app
- `markdown` - Converts markdown text to HTML with sanitization
- `format_datetime` - Formats ISO datetime strings to readable format
- `get_datetime` - Gets datetime field from objects, falling back to date if needed
- `get_alt_text` - Extracts alt text from GridFS image URLs using metadata ✅ (newly added)

**Still pending**:
- Responsive image filter with `srcset` and `sizes` attributes
- Image compression filter with quality settings

## 5. Testing Plan

1. **Performance Testing**: Verify that the changes improve the PageSpeed Insights performance score
2. **Accessibility Testing**: Use accessibility testing tools to verify the improvements
3. **Security Testing**: Verify that security headers are properly implemented
4. **Cross-browser Testing**: Ensure the changes work across different browsers
5. **Mobile Testing**: Test the responsive images and overall mobile experience

## 6. Implementation Status Summary

After implementing the initial improvement changes, we observed the following results from the updated PageSpeed Insights report:
- **Performance**: Increased from 63 to 84 (+21 points) ✅
- **Accessibility**: Increased from 94 to 98 (+4 points) ✅
- **Best Practices**: Recovered from 88 to 96 (+8 points recovery) ✅
- **SEO**: Remained at 100 (no change) ✅

### Key Achievements:
1. **Render-blocking resources optimization**: Critical CSS inlined, JS deferred, fonts optimized
2. **CSP implementation**: Policy with trusted CDN allowlists (nonce generation implemented but not enforced in CSP header)
3. **Modular architecture**: Successfully refactored monolithic `app.py` into a clean package structure
4. **NeoSQLite migration**: Complete database migration from MongoDB to NeoSQLite
5. **Modern stack**: Updated to Flask 3.1, Bootstrap 5.3, and modern Python practices

### Known Issues to Address:
1. **CSP nonce not enforced**: Nonce is generated and used in templates, but `_build_csp_policy()` doesn't inject it into the CSP header (no `"{nonce}"` in directive values). Inline scripts work via `'unsafe-inline'` fallback.
2. **CSS loading**: Bootstrap and Font Awesome use synchronous `<link rel="stylesheet">` instead of preload+onload pattern. This prevents FOUC but keeps resources render-blocking.
3. **No responsive images**: Images lack `srcset` and `sizes` attributes for responsive loading.
4. **WebP conversion**: Mentioned in plan but not implemented for uploaded images.

## 7. Regressions Addressed

The following regressions were identified and fixed during the implementation:

#### 7.1 Content Security Policy Blocking Resources ✅ FIXED
**Issue**: The initial CSP implementation was blocking Font Awesome fonts and highlight.js resources
- Font Awesome fonts (fa-brands-400, fa-regular-400, fa-solid-900, fa-v4compatibility) were being blocked
- Highlight.js scripts and stylesheets were being blocked
- Cloudflare analytics script was being blocked

**Resolution**:
- Updated CSP directives in `neo_bloggy/middleware/__init__.py` to allow trusted CDN sources
- Added proper CSP directives for font-src, script-src, and style-src

**Files modified**:
- `neo_bloggy/middleware/__init__.py` (updated CSP policy builder)

#### 7.2 Best Practices Score Decrease ✅ FIXED
**Issue**: Best Practices score decreased from 96 to 88 due to CSP warnings
- Host allowlists can frequently be bypassed
- `'unsafe-inline'` allows execution of unsafe in-page scripts
- CSP recommendations suggested using nonces or hashes instead

**Resolution**:
- Implemented nonce generation in `neo_bloggy/auth/__init__.py`
- Added nonce injection via context processor in `neo_bloggy/__init__.py`
- Updated all templates with `nonce="{{ csp_nonce }}"` attributes on inline scripts and styles
- ⚠️ **Note**: Nonce is generated and used in templates, but `_build_csp_policy()` does not inject it into the CSP header (no `"{nonce}"` placeholder in directive values). The nonce attributes work because `'unsafe-inline'` is still permitted.

**Files modified**:
- `neo_bloggy/middleware/__init__.py` (added nonce-based CSP)
- `neo_bloggy/auth/__init__.py` (added nonce functions)
- `neo_bloggy/__init__.py` (updated context processor)
- `templates/header.html` (added nonce to inline styles and scripts)
- `templates/footer.html` (added nonce to inline scripts)
- `templates/post.html` (added nonce to inline scripts)
- `templates/create_post.html` (added nonce to inline scripts)
- `templates/upload.html` (added nonce to inline scripts)

## 8. Expected Outcomes

The following outcomes have been achieved through the implementation:

- **Performance score improvement**: ✅ Achieved - Improved from 63 to 84 (+21 points)
  - Critical CSS inlined for above-fold content
  - JavaScript deferred with `defer` attributes
  - Font optimization with `display=swap` and fallback fonts
  - Image optimization with lazy loading and fetchpriority attributes
  - Jumbotron images preloaded conditionally
  - ⚠️ CSS resources still loaded synchronously (Bootstrap, Font Awesome) to prevent FOUC

- **Accessibility score improvement**: ✅ Achieved - Improved from 94 to 98 (+4 points)
  - Fixed unnamed links with proper aria-labels
  - Fixed heading hierarchy (h5 → h3 for post titles)

- **Security improvements**: ⏳ Mostly Achieved
  - Implemented CSP with trusted CDN allowlists
  - Added HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy headers
  - Added Cross-Origin-Opener-Policy header
  - HTML minification implemented
  - ⚠️ CSP nonce not enforced in header (works via `'unsafe-inline'` fallback)
  - ⚠️ `'unsafe-inline'` still permitted in script-src and style-src

- **Better overall user experience**: ✅ Achieved
  - Faster loading times through resource optimization
  - Improved Core Web Vitals scores

- **SEO maintained**: ✅ Achieved - Remained at 100/100

## 9. Current Implementation Status

### Completed Items ✅:
1. **Modular Architecture**
   - ✅ Modular project structure with Application Factory and Blueprints
   - ✅ Service Layer separating business logic from routes
   - ✅ NeoSQLite database migration (replaced MongoDB/PyMongo)

2. **Performance Optimizations**
   - ✅ Critical CSS inlining for above-fold content
   - ✅ Preconnect hints for third-party domains (jsdelivr, fontawesome, fonts.googleapis)
   - ✅ Image optimization with width, height, loading and fetchpriority attributes
   - ✅ Font optimization with display=swap and fallback fonts with size-adjust
   - ✅ HTML minification
   - ✅ JavaScript defer attributes in footer
   - ✅ Jumbotron image preloading (conditional based on page)
   - ⚠️ CSS loading: Bootstrap/Font Awesome use synchronous loading (not preload+onload)

3. **Security Implementation**
   - ✅ CSP headers with trusted CDN allowlists
   - ✅ Security headers (HSTS, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy)
   - ✅ Cross-Origin-Opener-Policy header
   - ✅ Nonce generation and template injection (⚠️ not enforced in CSP header)
   - ✅ Input validation and XSS protection

4. **Accessibility Improvements**
   - ✅ Fixed unnamed links with proper aria-labels
   - ✅ Fixed heading hierarchy (h5 → h3)
   - ✅ Social media links updated (Twitter → X)

5. **Template Updates**
   - ✅ All templates updated with CSP nonces on inline scripts/styles
   - ✅ Blueprint-prefixed `url_for` calls
   - ✅ Image loading optimizations
   - ✅ `get_alt_text` template filter for GridFS image alt text

### Items Still Pending ⏳:
1. **Advanced Image Optimization**
   - ⏳ Implement responsive images with `srcset` and `sizes` attributes
   - ⏳ Add server-side image resizing to generate multiple image sizes
   - ⏳ Add image compression with configurable quality settings
   - ⏳ Implement Jinja2 template filter for responsive images
   - ⏳ WebP conversion for uploaded images (mentioned in plan, not implemented)

2. **Code Optimization**
   - ⏳ Remove unused CSS and JavaScript from CDN bundles
   - ⏳ Audit and remove unused Bootstrap components
   - ⏳ Optimize EasyMDE editor bundle (already lazy-loaded per-page)

3. **CSP Nonce Enforcement**
   - ⏳ Fix `_build_csp_policy()` to inject nonce into `script-src` and `style-src`
   - ⏳ OR remove nonce attributes from templates if `'unsafe-inline'` is intentionally kept

### Notable Current State:
- The monolithic `app.py` has been refactored into a modular `neo_bloggy` package
- The CSP implementation uses CDN allowlists; nonce is generated but **not enforced** in the CSP header
- All templates use `nonce="{{ csp_nonce }}"` on inline scripts/styles (works via `'unsafe-inline'` fallback)
- Image loading optimized with width/height attributes, lazy loading, and fetchpriority
- Full accessibility compliance implemented
- Social media links use X instead of Twitter
- Complete database migration to NeoSQLite with MongoDB-like API
- Asian language search support available via custom FTS5 tokenizers
- `base_url` in `config.toml` is empty (canonical URLs fall back to `request.url`)

## 10. Future Improvements

### 10.0 Immediate Priorities (from April 2026 verification audit)
1. **CSP Nonce Enforcement** - Fix `_build_csp_policy()` to properly inject `'nonce-<value>'` into `script-src` and `style-src` directives, or remove nonce attributes from templates if `'unsafe-inline'` is intentionally kept
2. **Responsive Images** - Implement `srcset` and `sizes` attributes for post card images
3. **Canonical URL Configuration** - Set `base_url` in `config.toml` to the production domain (`https://neo.bashell.com/`) for proper canonical URLs

### 10.1 Database Performance Optimization (NeoSQLite Aggregation Pipeline)

**Overview**: Leverage NeoSQLite's MongoDB-compatible aggregation pipeline to reduce database round trips, eliminate Python-side filtering, and enable new analytics capabilities. NeoSQLite (`v1.14.2`) provides 100% PyMongo-compatible API including `$lookup`, `$unwind`, `$group`, `$facet`, `$textScore`, `$setWindowFields`, and 20+ other stages.

**Current State**: The application uses basic CRUD operations with multiple separate queries where single aggregation pipelines could suffice.

**Key Opportunities** (12 identified):

#### Tier 1 - Highest ROI (No `$facet` dependency):

**1. Post + Comments Aggregation** (CRITICAL)
- **Current**: 3 queries (post + comments + active users) + Python filtering
- **Target**: 1 aggregation pipeline with `$lookup`
- **Benefit**: ~50-60% reduction in database round trips
- **File**: `neo_bloggy/posts/helpers.py` - `get_post_with_comments()`

**2. Advanced Tag Analytics**
- **Current**: O(n) Python loop through all posts to collect tags
- **Target**: `$unwind` + `$group` aggregation
- **Benefit**: Exponential scaling improvement
- **File**: `neo_bloggy/services/__init__.py` - `posts_by_tag()`

**3. Search with Relevance Scoring**
- **Current**: Manual Python scoring after query
- **Target**: Native `$textScore` sorting via aggregation
- **Benefit**: Better accuracy + server-side sorting
- **File**: `neo_bloggy/search/__init__.py`

**4. Comment Moderation Queue** (NEW FEATURE)
- **Current**: Not implemented (would require multiple queries)
- **Target**: Single `$lookup` pipeline joining comments + posts + users
- **Benefit**: New capability for content moderation

#### Tier 2 - Code Clarity Wins (`$facet` for organization):

**Note**: NeoSQLite executes `$facet` sub-pipelines sequentially. Benefits come from code organization and reduced API round trips, not parallel speedup.

**5. Paginated Post Listing**
- **Current**: 2-3 separate queries (posts + count + author info)
- **Target**: `$facet` pipeline for posts + pagination metadata
- **Benefit**: Code clarity + ~40-50% reduction

**6. Admin Dashboard Analytics**
- **Current**: 6+ separate queries for dashboard metrics
- **Target**: 2 organized `$facet` pipelines
- **Benefit**: Atomic snapshot + code organization

**7. User Profile Analytics**
- **Current**: Multiple queries for posts, drafts, comments
- **Target**: 1-2 aggregation pipelines
- **Benefit**: Real-time statistics

#### Tier 3 - Advanced Features:

**8. Content Recommendations**
- `$lookup` with `$setIntersection` for similar tags
- Enables "related posts" feature

**9. Time-Based Analytics**
- Monthly post counts via `$dateFromString` + `$group`
- Author performance metrics

**10. GridFS Metadata Queries**
- Find unused images via `$lookup` on blog_posts
- Storage optimization opportunities

**11. Bulk Operations Optimization**
- Replace loops with `update_many`
- Atomic migrations

**NeoSQLite Compatibility Notes**:
- `$facet` runs sequentially (not parallel) - position as code clarity tool
- `$lookup`, `$unwind`, `$group` provide biggest wins
- Test each pipeline with your NeoSQLite version
- Keep fallback implementations initially

**Implementation Strategy**:
1. Start with Tier 1 (Post + Comments aggregation)
2. Add monitoring for query execution times
3. Validate pipelines with NeoSQLite version
4. Gradually migrate with feature flags

**Expected Impact**:
- 40-60% reduction in database API calls for common operations
- Exponential scaling for tag analytics
- New features (moderation, recommendations)
- Cleaner codebase with less Python filtering

---

### 10.1 Frontend Performance Enhancements
1. **Image Optimization** *(See Section 1.2 and Section 9 for pending items)*
   - Consolidated pending items: responsive images, server-side resizing, compression

2. **Bundle Optimization** *(See Section 1.3 and Section 9 for pending items)*
   - Consolidated pending items: unused CSS/JS removal, EasyMDE optimization

3. **Caching Strategy**
   - Implement service worker for offline support
   - Add HTTP caching headers for static assets
   - Optimize cache invalidation strategy

### 10.2 Security Enhancements
1. **CSP Hardening** *(See Section 3.1 for current implementation)*
   - Remove `'unsafe-inline'` where possible
   - Implement stricter CSP policies via web server configuration
   - Add CSP reporting endpoint

2. **Additional Security Headers**
   - Permissions-Policy header
   - Cross-Origin-Resource-Policy header
   - Cross-Origin-Embedder-Policy header

### 10.3 Accessibility Enhancements
1. **WCAG 2.1 AA Compliance**
   - Add skip navigation links
   - Improve focus indicators
   - Add ARIA landmarks
   - Test with screen readers

### 10.4 Developer Experience
1. **Testing**
   - Add unit tests for utils functions
   - Add integration tests for routes
   - Add E2E tests for critical user flows

2. **Documentation**
   - API documentation
   - Deployment guides
   - Contributing guidelines

---

## Document History

- **April 2026**: Full codebase verification audit. Updated completion status to reflect actual implementation state:
  - Section 1.1: Changed render-blocking resources from ✅ to ⏳ PARTIALLY (CSS uses synchronous loading, not preload+onload)
  - Section 1.3: Updated unused CSS/JS section with current state analysis
  - Section 3.1: Changed security headers from ✅ to ⏳ MOSTLY (CSP nonce not enforced in header)
  - Section 3.4: Corrected - WebP conversion not implemented despite plan claiming it
  - Section 3.5: Added `get_alt_text` filter to completed list
  - Section 4.1: Updated to reflect actual synchronous CSS loading
  - Section 6-9: Added "Known Issues to Address" section with 4 specific items
  - Section 10.0: Added immediate priorities from audit findings
  - Section 10.1: Updated to reflect NeoSQLite v1.14.2 with 100% PyMongo-compatible aggregation pipeline
- **April 2026**: Merged MongoDB aggregation pipeline optimization analysis into this document.
- **February 2026**: Initial PageSpeed Insights improvement plan created
