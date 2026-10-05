# Deploy as a second independent Streamlit app

To replace your existing app, use **UPDATE_SAME_GITHUB_REPO.md** instead. The instructions below keep that app separate.

1. Extract the supplied ZIP on your computer. Open the `hydroscope_water_research` folder.
2. Sign in to GitHub. Click **New repository**. Name it `hydroscope-water-research` and create it.
3. Upload all contents of the extracted folder, retaining `.streamlit/`, `examples/` and `tests/` as folders. `app.py` and `requirements.txt` must be at the top level. Do not upload only `app.py`, a ZIP, or flattened files from subfolders.
4. Commit the files to `main`.
5. Sign in at [share.streamlit.io](https://share.streamlit.io/) with GitHub. Choose **Create app / Deploy an app**, then select this repository.
6. Select branch **main** and main file path **app.py**.
7. In Advanced settings select **Python 3.12**. No build command is needed. Dependencies are read from `requirements.txt`.
8. Leave Secrets empty for a fully usable non-AI app. To enable the optional interpreter, copy the relevant provider entries from `secrets.example.toml` and enter your actual key privately in Secrets.
9. Click Deploy. Wait for dependency installation. If it fails, open the build log and confirm Python 3.12 and the full folder structure before changing package versions.
10. Open the app, save a water study and test your field dataset. Satellite and model data access depends on the source's coverage and availability.

The Python version in Streamlit deployment settings is authoritative; `.python-version` helps local tools but does not change an existing cloud runtime by itself.

For local use: install Python 3.12, run `python -m pip install -r requirements.txt`, then `python -m streamlit run app.py` from the project folder.

References: [Streamlit deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [dependency files](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), [secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).
