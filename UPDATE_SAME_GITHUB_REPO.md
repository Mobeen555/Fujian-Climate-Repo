# Replace the old app in the same GitHub repository

**Result:** the repository and existing Streamlit app link stay the same. Its code and displayed name become **HydroScope Water Research**. This is a complete replacement project, not a single-file patch. Keep `app.py` at the top level.

Do this on a computer if possible. No terminal commands are necessary. Do not delete the GitHub repository or the deployed Streamlit app.

## 1. Make a backup

1. Sign in to GitHub and open the repository connected to your current Streamlit application.
2. Click the green **Code** button → **Download ZIP**. Keep that old ZIP separately.
3. Record the current deployed branch (usually `main`) and entrypoint. Keep a private copy of any Streamlit Secrets you still need. Do not put keys in GitHub.
4. Download and extract `HydroScope_Water_Research_Streamlit_v1.0.zip` from this delivery. Open the extracted `hydroscope_water_research` folder. You should see `app.py` and `requirements.txt` inside it.

## 2. Recommended: replace everything in one GitHub Desktop commit

This avoids deploying a partly updated set of files.

1. Install [GitHub Desktop](https://desktop.github.com/) and sign in to your GitHub account.
2. Choose **File → Clone repository**. Select the existing app repository and click **Clone**. This makes a local copy linked to the SAME repository; it does not create a new one.
3. Select the branch used by Streamlit, usually **main**. Click **Fetch origin / Pull origin** if updates are available.
4. Choose **Repository → Show in Explorer** on Windows, or **Show in Finder** on Mac.
5. Inside that local repository folder, remove the old app's source files and folders. **Keep the `.git` folder**; it stores the connection and history. Do not delete the local repository folder itself. If this repository contains unrelated work, preserve that work separately and replace only this app's files.
6. Open the extracted new `hydroscope_water_research` folder. Copy **all its contents**, including `.streamlit`, `.gitignore`, `.python-version`, `examples` and `tests`, directly into the local repository folder. Replace old files when asked. Do not copy the enclosing project folder as an extra nested level. Enable hidden-file visibility if needed to include the dot-prefixed configuration files.
7. Return to GitHub Desktop. The Changes list should show removed old files and added/modified new files. Confirm `app.py` and `requirements.txt` are at the top level. Confirm no real API key or `.streamlit/secrets.toml` is included.
8. In Summary, type **Replace old app with HydroScope water-only research**.
9. Click **Commit to main** (or your deployed branch), then **Push origin**. If branch protection requires a pull request, use a replacement branch and merge it into the deployed branch through GitHub.
10. Open the repository on GitHub and refresh. Confirm the new README and `app.py` are visible.

Every file in the new ZIP belongs to the replacement project. There must be no leftover `agents/`, `crew_config.py`, `crew_workflow.py`, `crew_runtime.py`, `crewai_compat.py`, `agent_common.py` or `agent_tools.py` in this new app. Keep the **new** `evidence.py`: the interpreter and reports still use it. Replace the old `requirements.txt` completely so CrewAI is not reinstalled.

## 3. If you only use the GitHub website

Use a temporary branch so the live app keeps working during the replacement.

1. On the repository page, open the branch dropdown, type `hydroscope-water-update` and create that branch from the deployed branch.
2. On this new branch, open each old file → top-right **… → Delete file → Commit changes**. For an old folder, open it → **… → Delete directory → Commit changes**. Keep deleting the old app contents until ready to upload the full new project. Do not delete the repository.
3. Return to the root of this new branch. Click **Add file → Upload files**.
4. Drag the **contents inside** the extracted new project folder into the upload area, preserving folders. Upload source files and folders, not the ZIP itself and not a flattened list taken out of all folders. Commit to `hydroscope-water-update`.
5. Verify `.streamlit/config.toml`, `.gitignore` and `.python-version` arrived. If hidden files did not upload, use **Add file → Create new file**, enter the exact path, paste that file's content from the ZIP and commit it on this branch.
6. Confirm `app.py`, `environment.py`, `water_data.py`, `evidence.py`, `interpretation.py`, `ai_providers.py` and `requirements.txt` are at the root. Do not leave the enclosing `hydroscope_water_research/` folder above them.
7. Use **Compare & pull request** to compare `hydroscope-water-update` into the deployed branch. Review the changed files, then **Merge pull request**. The live app receives the complete replacement together.

GitHub's file/directory deletion UI and upload UI may vary slightly; use the official links below if a menu is not visible. GitHub Desktop is easier for replacing a whole folder.

## 4. Refresh the existing Streamlit deployment

1. Go to [share.streamlit.io](https://share.streamlit.io/) and open the existing app's management/settings.
2. Keep the same connected repository and deployed branch.
3. The main file path for this package is **`app.py`**. Do not select `api`, a folder, or `requirements.txt`. If the existing deployment was already using root `app.py`, no path change is needed. If it uses another path, align the source location or deployment configuration before updating; do not create duplicate conflicting entrypoints.
4. Use **Python 3.12**. The `.python-version` file documents the target; it does not override Streamlit Cloud's Python setting. If the existing app uses a different Python runtime and the service does not expose an in-place change, follow Streamlit's Python-upgrade instructions (a redeploy may be required).
5. Streamlit automatically pulls committed changes on the connected branch. A changed `requirements.txt` triggers dependency handling; allow it to finish.
6. If the page remains on the old version after the build completes, choose **Reboot app** in the management menu and refresh your browser. Look for **HydroScope Water Research** and a **Waterbody type** selector.
7. Open **Water study**, choose a waterbody and save an empty-source study. Open **Water research** to confirm uploads work. Then test one real satellite or water-model request at a location/date with coverage.

The browser URL can retain its old `fujian-climate...streamlit.app` name. The app's title and scope have changed. Renaming a URL is optional and independent of replacing code.

## 5. Optional AI interpretation settings

The app works immediately **without any AI key**. You can skip this section.

To reuse a Gemini key, keep these entries in Streamlit **Settings → Secrets**, or use the provider you already have:

```toml
AI_PROVIDER = "gemini"
GEMINI_API_KEY = "YOUR_ACTUAL_KEY"
GEMINI_MODEL = "gemini-3.5-flash-lite"
```

Only the model name is ordinary configuration. Replace `YOUR_ACTUAL_KEY` privately with your real key. Check current provider access if a model is unavailable; edit the model ID in Secrets or the interpreter form. `secrets.example.toml` lists Groq/OpenRouter alternatives. None of these providers guarantees unlimited free usage.

Old agent budgets such as `AI_REQUESTS_PER_MINUTE` and `AI_TOKENS_PER_MINUTE` are no longer used and can be removed. Remove any no-longer-used CrewAI, Supabase or Vercel-only settings. Keep only the provider credentials you actually want. There is no `VERCEL_SUPPORT_LARGE_FUNCTIONS` setting in this Streamlit project.

Inside the app, open **AI interpretation** only after computed results exist. Inspect the displayed evidence summary, confirm sending it to the provider, then click **Interpret saved results**. The same saved request is reused until the evidence/question/provider/model changes.

## Recovery

The old version remains in Git history and in your downloaded backup. If a deployment fails, read the Streamlit build/runtime log first. A missing local module usually means a source file is absent or in the wrong folder. In GitHub Desktop, reverting the replacement commit and pushing restores the previous committed files; do not paste old and new app components together.

## Official references

- [Clone with GitHub Desktop](https://docs.github.com/en/desktop/adding-and-cloning-repositories/cloning-and-forking-repositories-from-github-desktop)
- [Delete GitHub files and folders](https://docs.github.com/en/repositories/working-with-files/managing-files/deleting-files-in-a-repository)
- [Upload files to GitHub](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)
- [Streamlit updates from repository commits](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/edit-your-app)
- [Streamlit app settings](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings)
- [Streamlit reboot](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/reboot-your-app)
- [Streamlit Python runtime changes](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/upgrade-python)
