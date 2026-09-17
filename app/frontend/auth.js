const ACCESS_TOKEN_STORAGE_KEY = "fitness_tracker_access_token";

function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
}

function saveAccessToken(accessToken) {
  localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, accessToken);
}

function clearAccessToken() {
  localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}

function getAuthHeaders(headers = {}) {
  const token = getAccessToken();

  return {
    ...headers,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

let isRedirectingToLogin = false;

async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: getAuthHeaders(options.headers),
  });

  if (response.status === 401) {
    clearAccessToken();

    const currentPath = (
      `${window.location.pathname}${window.location.search}`
    );

    if (
      !isRedirectingToLogin
      && !window.location.pathname.startsWith("/static/login/")
    ) {
      isRedirectingToLogin = true;

      window.location.href = (
        `/static/login/?next=${encodeURIComponent(currentPath)}`
      );
    }
  }

  return response;
}