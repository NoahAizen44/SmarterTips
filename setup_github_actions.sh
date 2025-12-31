#!/bin/bash
# Quick setup script to push everything to GitHub

echo "🚀 Setting up GitHub Actions for Daily NBA Updates"
echo "=================================================="
echo ""

cd /Users/noaha/smartertips

echo "1️⃣ Adding all files..."
git add .

echo ""
echo "2️⃣ Committing changes..."
git commit -m "Add daily update automation with GitHub Actions"

echo ""
echo "3️⃣ Pushing to GitHub..."
git push origin main

echo ""
echo "✅ Code pushed to GitHub!"
echo ""
echo "📋 Next steps:"
echo "1. Go to: https://github.com/NoahAizen44/SmarterTips/settings/secrets/actions"
echo "2. Click 'New repository secret'"
echo "3. Name: NEON_DSN"
echo "4. Value: Your database connection string"
echo "5. Go to Actions tab and test it!"
echo ""
echo "📖 Full instructions: See GITHUB_ACTIONS_SETUP.md"
