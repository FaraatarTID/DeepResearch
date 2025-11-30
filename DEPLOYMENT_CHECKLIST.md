# Streamlit Cloud Deployment Checklist

## Pre-Deployment Checklist

- [ ] **Code is ready**

  - [ ] All dependencies listed in `requirements.txt`
  - [ ] App runs locally with `streamlit run app.py`
  - [ ] No hardcoded secrets in code
  - [ ] `.gitignore` properly configured

- [ ] **GitHub Repository**

  - [ ] Code pushed to GitHub
  - [ ] Repository is public or you have Streamlit Cloud access to private repos
  - [ ] Main branch is up to date

- [ ] **API Keys Ready**
  - [ ] Gemini API Key (from Google AI Studio)
  - [ ] Brave Search API Key
  - [ ] Unpaywall Email address

## Deployment Steps

### 1. Push to GitHub

```bash
# If not already initialized
git init
git add .
git commit -m "Ready for Streamlit deployment"

# If repository doesn't exist yet
# Create a new repository on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main

# If repository already exists
git add .
git commit -m "Update for deployment"
git push
```

### 2. Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click "New app"
4. Fill in:
   - **Repository**: YOUR_USERNAME/YOUR_REPO_NAME
   - **Branch**: main
   - **Main file path**: app.py
5. Click "Advanced settings" (optional)
6. Add secrets in TOML format:

```toml
GEMINI_KEY = "your-actual-gemini-api-key-here"
BRAVE_API_KEY = "your-actual-brave-api-key-here"
UNPAYWALL_EMAIL = "your-email@example.com"
```

7. Click "Deploy!"

### 3. Post-Deployment

- [ ] App deployed successfully
- [ ] Test the app with a sample research query
- [ ] Verify downloads work (DOCX, Markdown, Bibliometrics)
- [ ] Check logs for any errors
- [ ] Share the app URL!

## Troubleshooting

### Build Fails

- Check the build logs in Streamlit Cloud
- Verify all packages in `requirements.txt` are correct
- Ensure Python version compatibility

### App Crashes on Startup

- Check if all secrets are properly set
- Verify API keys are valid
- Look for import errors in logs

### API Errors During Research

- Verify API keys have proper permissions
- Check API quotas/limits
- Ensure API keys are correctly formatted in secrets

### Slow Performance

- Consider reducing default search rounds
- Check if you're hitting API rate limits
- Monitor Streamlit Cloud resource usage

## Updating Your Deployed App

Simply push changes to your GitHub repository:

```bash
git add .
git commit -m "Description of changes"
git push
```

Streamlit Cloud will automatically detect changes and redeploy!

## Resources

- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- [Secrets Management](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)
- [App Settings](https://docs.streamlit.io/streamlit-community-cloud/manage-your-app)
