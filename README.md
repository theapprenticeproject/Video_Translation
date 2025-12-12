# Video Localizer - Translator
***An automated video localizer/translator for native Indian languages.***

## 📋 Table of Contents 
- [Features](#-features)
- [Documentation](#-documentation)
- [Testing APIs Locally](#-testing-apis-locally)
- [Installation](#-installation)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features
* Localizes videos into multiple Indic languages.
* Built on the **Frappe framework** with background queues to handle concurrent uploads.
* Supports lip-sync for videos, along with translated subtitles for all outputs.
* Enables educators to create profiles and translate video content with a single button click.
* Generates all components of a localized video — subtitles, translated audio, and more.
* Provides versioned APIs for easier pipeline extension.
* Uses **uv** for fast and reliable package & dependency management.

## 📑 Documentation
Full setup guides, architecture, API Flows, etc., are available in the **[Gitbook Documentation ↗](https://theapprenticeproject.gitbook.io/ai-video-localization/RbOX32eTbHDcOMXmXgoF/)**

## 📦 Installation
### Bench Installation
You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app git@github.com:theapprenticeproject/Video_Translation.git --branch main
bench install-app my_app
```
**Note: Manually create the  `/original` & `/processed` folders under site's public directory (`sites/[your_site_name]/public/files/`).** 

## 🧪 Testing APIs Locally
For quick sanity checks, you can check the sample file at `www/test-video.html`. It is a simple UI for testing APIs directly in the browser.
* Run `bench start` in the terminal.
* Open the file in the browser at `localhost:8000/test-video`.
* Modify/Alter endpoints/functions as per request bodies (as these endpoints are integrated with queues).
* Update the **Authorization** header if requires credentials (functions are whitelisted).
* Select the endpoint in dropdown and click **Run Test**(e.g., `ping`, etc).
* The JSON response will be displayed on the page. You can add more endpoints in the `www/test-video.html` for testing.
   <img width="700" alt="image" src="https://github.com/user-attachments/assets/7ca935a8-a284-478d-b317-bcdea54a5704" />
   > Subtitle generate API testing using token-based auth.
  
---

## 🤝 Contributing
For all future contributions:
* Follow the [Setup Guide ↗](https://theapprenticeproject.gitbook.io/ai-video-localization/RbOX32eTbHDcOMXmXgoF/getting-started) in the docs to set up locally.
* This project follows [Conventional Commits ↗](https://www.conventionalcommits.org/) (adopted from mid-development onwards).
* Check **Issues** for past progress and future tracking.
* #### Code Style (Optional)
    * We use ***ruff*** (python) and *prettier* (JS/JSON) for consistent formatting.
    * `pre-commit` is for code formatting and linting. An optional [install pre-commit](https://pre-commit.com/#installation) config is included in repo if required automatic checks, enable it:

        ```bash
        cd apps/my_app
        pre-commit install
        ```
    * Pre-commit is configured to use *ruff, eslint, prettier, pyupgrade* for checking and formatting your code

## 📜 License

The project is licensed under the MIT License. See the [LICENSE file ↗](https://github.com/theapprenticeproject/Video_Translation/) for details.
