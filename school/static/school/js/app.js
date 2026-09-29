document.body.addEventListener("htmx:configRequest", function (event) {
    const token = document.querySelector('meta[name="csrf-token"]');
    if (token) {
        event.detail.headers["X-CSRFToken"] = token.content;
    }
});

document.body.addEventListener("htmx:responseError", function (event) {
    const status = event.detail.xhr.status;
    const container = document.getElementById("flash-container");
    if (!container) return;

    let text = "ያልታወቀ ስህተት ተከስቷል።";
    if (status === 403) text = "ይህን ለማድረግ ፈቃድ የለዎትም።";
    if (status === 404) text = "የተጠየቀው ነገር አልተገኘም።";
    if (status >= 500) text = "የሰርቨር ስህተት ተከስቷል፣ እንደገና ይሞክሩ።";

    const div = document.createElement("div");
    div.className = "mb-4 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800";
    div.textContent = text;
    container.prepend(div);
});