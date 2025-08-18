# IncomeTaxAI: Your Private, AI-Powered Tax Filing Assistant

<p align="center">
  <img src="https://i.imgur.com/example.png" alt="IncomeTaxAI Logo" width="200">
</p>

<p align="center">
  <strong>File your Indian income tax returns with confidence and complete privacy.</strong>
</p>

---

## About

IncomeTaxAI is an open-source, AI-powered tool that simplifies the process of filing Indian income tax returns. It uses an AI model to analyze your tax documents, calculate your tax liability, and guide you through the filing process, ensuring that your financial data remains completely private.

## Motivation

As a regular taxpayer, I found the process of computing income tax and understanding all the different sections to be confusing and time-consuming. I wanted to create a tool that would empower everyday users to file their taxes accurately and without the need to hire a professional. IncomeTaxAI is designed to guide you on what to fill, where to fill it, and why—so you can file with confidence.

### The Problem

*   **Complex rules, scattered info:** The Indian tax system is complex, with numerous sections, regimes, deductions, and forms that are difficult for non-experts to understand and piece together.
*   **High effort, high anxiety:** Manual calculations and the fear of making mistakes can lead to anxiety, errors, and missed tax-saving opportunities.
*   **Tools lack guidance:** Most tax calculators provide you with numbers but don't offer the step-by-step guidance needed to fill out the official tax portal correctly.

### The Solution

IncomeTaxAI is designed to address these challenges by providing a user-friendly, privacy-focused solution for Indian taxpayers. Our goal is to make tax filing simple, transparent, and secure for everyone.

## Key Features

*   **AI-Powered Document Analysis:** Automatically extract data from your Form 16, bank statements, investment proofs, and other tax documents.
*   **Dual Tax Regime Comparison:** Compare your tax liability under both the old and new tax regimes to maximize your savings.
*   **Step-by-Step Guidance:** Get clear instructions on how to fill out the official income tax portal.
*   **Privacy First:** Your financial data is encrypted on your device before being uploaded, and is only decrypted in-memory for processing.
*   **Open Source:** The code is open source and auditable, so you can be sure that your data is safe.

## How it Works

1.  **Upload Your Documents:** Upload your tax documents (Form 16, bank statements, etc.) to the tool.
2.  **AI-Powered Analysis:** The tool's AI model analyzes your documents and extracts the relevant information.
3.  **Review and Calculate:** Review the extracted data and let the tool calculate your tax liability under both tax regimes.
4.  **File with Confidence:** Use the generated information and step-by-step guidance to file your taxes on the official income tax portal.

## Privacy First

With the rise of large, professional tax-filing platforms, there is a real risk that your sensitive financial data could be stored, profiled, or shared. We believe that your financial data should be yours—period.

IncomeTaxAI is built to be private by default. Here's how we protect your privacy:

*   **End-to-End Encryption:** Your tax documents are encrypted on your device before they are uploaded to our server. They remain encrypted on our server and are only decrypted in memory when they are being processed.
*   **In-Memory Processing:** Your encrypted documents are decrypted in memory for analysis. We never write your decrypted financial data to disk on our servers.
*   **No Data Collection:** We do not collect, store, or transmit your personal information. There are no user accounts, and we do not use any tracking or analytics services.
*   **Open Source and Auditable:** Our code is open source, so you can inspect it yourself to verify that we are living up to our privacy promises.

## Installation Guide

### System Requirements

*   **OS:** macOS, Linux, or Windows
*   **RAM:** Minimum 8GB (16GB recommended)
*   **Storage:** 10GB free space
*   **Docker:** Docker and Docker Compose
*   **Internet:** Required for downloading the AI model

### Installation Steps

1.  **Install Ollama and the AI Model:**

    ```bash
    # On macOS
    brew install ollama

    # On Linux
    curl -fsSL https://ollama.ai/install.sh | sh

    # On Windows, download from https://ollama.ai/download
    ```

    Once Ollama is installed, start it and download the AI model:

    ```bash
    ollama serve
    ollama pull Qwen2.5:3b
    ```

2.  **Clone and Run the Application:**

    ```bash
    git clone <your-repo-url>
    cd incometax_project
    ./setup_hybrid.sh
    ```

3.  **Access the Application:**

    Open your browser and go to: `http://localhost:8000`

## Contributing

We welcome contributions from the community! If you would like to contribute to the project, please read our `CONTRIBUTING.md` file for more information.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

---

<p align="center">
  <strong>Your Privacy, Your Savings, Your Control.</strong>
</p>
