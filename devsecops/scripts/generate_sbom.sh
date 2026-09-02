#!/bin/bash
# =============================================================================
#  SecureMed — SBOM Generator (Software Bill of Materials)
#  Generates CycloneDX SBOM for Python + Node.js components
# =============================================================================

set -euo pipefail

OUTPUT_DIR="${1:-./sbom}"
mkdir -p "$OUTPUT_DIR"
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)

echo "🔍 Generating SBOM for SecureMed..."
echo "   Output: $OUTPUT_DIR"
echo "   Timestamp: $TIMESTAMP"

# ─── Python SBOM (cyclonedx-bom) ─────────────────────────────────────────────
echo ""
echo "📦 Python dependencies (CycloneDX)..."
if command -v cyclonedx-py &>/dev/null; then
    cd backend
    if [ -d venv ]; then
        . venv/bin/activate
    fi
    cyclonedx-py environment \
        --output-format json \
        --output-file "../${OUTPUT_DIR}/sbom-python-${TIMESTAMP}.json" \
        --schema-version 1.5 \
        2>/dev/null || echo "   ⚠️  cyclonedx-py failed, using pip-licenses fallback"

    # Fallback: pip-licenses
    if command -v pip-licenses &>/dev/null; then
        pip-licenses \
            --format=json \
            --output-file="../${OUTPUT_DIR}/sbom-python-licenses-${TIMESTAMP}.json" \
            2>/dev/null || true
    fi
    cd ..
else
    echo "   ⚠️  cyclonedx-py not installed — install with: pip install cyclonedx-bom"
    # Minimal fallback: freeze requirements
    cd backend
    if [ -d venv ]; then
        . venv/bin/activate
        pip freeze > "../${OUTPUT_DIR}/python-requirements-locked-${TIMESTAMP}.txt"
        echo "   ✅ Saved locked requirements to sbom/"
    fi
    cd ..
fi

# ─── Node.js SBOM ─────────────────────────────────────────────────────────────
echo ""
echo "📦 Node.js dependencies (CycloneDX)..."
if command -v cyclonedx-npm &>/dev/null; then
    cd frontend
    cyclonedx-npm \
        --output-format JSON \
        --output-file "../${OUTPUT_DIR}/sbom-nodejs-${TIMESTAMP}.json" \
        --schema-version 1.5 \
        2>/dev/null || echo "   ⚠️  cyclonedx-npm failed"
    cd ..
else
    echo "   ⚠️  @cyclonedx/cyclonedx-npm not installed"
    echo "      Install: npm install -g @cyclonedx/cyclonedx-npm"
    # Fallback: npm list
    cd frontend
    npm list --json > "../${OUTPUT_DIR}/nodejs-packages-${TIMESTAMP}.json" 2>/dev/null || true
    echo "   ✅ Saved npm package list to sbom/"
    cd ..
fi

# ─── AI Service SBOM ──────────────────────────────────────────────────────────
echo ""
echo "📦 AI service Node.js..."
cd ai-service
npm list --json > "../${OUTPUT_DIR}/sbom-ai-service-${TIMESTAMP}.json" 2>/dev/null || true
cd ..

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "✅ SBOM generation complete!"
echo ""
ls -lh "${OUTPUT_DIR}/"
echo ""
echo "📋 Files generated in: ${OUTPUT_DIR}/"
echo "   Use these files for:"
echo "   - Supply chain security review"
echo "   - License compliance check"
echo "   - Vulnerability correlation (Grype, OWASP Dependency Track)"
