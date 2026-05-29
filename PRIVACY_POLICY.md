# Privacy Policy / 隱私政策

**Last Updated: 2026-05-29**

## English Version

Agentmux ("we," "our," or "the App") is committed to protecting your privacy. This policy outlines our approach to data security and privacy.

### 1. No Data Collection & Client-Side Operation
Agentmux is a tool designed for developers. We **DO NOT** collect, store, or transmit any of your personal data, server credentials, or terminal traffic to our own servers or any third parties. All operations are conducted locally on your device or directly over SSH to your servers.

### 2. Client-Side AI Bridge (Optional)
Agentmux acts as a secure, client-side SSH bridge to your remote server. The App itself does not directly provide, host, or run any AI models or services. Instead, it allows you to interact with AI Coding Agents (such as Claude, Gemini, etc.) and custom agents that you have installed and configured on your own remote server.
- **What is processed**: When you choose to run these agents, the input prompts, terminal command history, and selected workspace files you interact with are sent through your SSH connection to perform coding tasks on your server.
- **Who it is sent to**: The data is processed directly by the third-party AI CLI tools and model providers (e.g., Anthropic, Google, OpenAI, etc.) that you set up on your remote server using your own API credentials.
- **No Client Interception**: All data transmission occurs peer-to-peer over your SSH connection. Agentmux does not intercept, collect, log, or track any of this codebase context or AI prompt inputs. By using these optional features, you authorize the transmission of this workspace data to the AI service providers configured on your server.

### 3. Local Storage & Security
- **SSH Credentials**: Your passwords and private keys are stored exclusively in the iOS system **Keychain**. We use industry-standard encryption provided by Apple to ensure your credentials remain secure.
- **Server Information**: All server configurations and project paths are stored locally on your device via **SwiftData**. 
- **Terminal Traffic**: All communication between the App and your server is encrypted via the **SSH protocol**. We do not intercept or log your terminal output.

### 4. Command Transparency & Security
- **Automated Probes**: To provide features like path detection and tmux management, Agentmux executes non-destructive probe commands (e.g., `PATH`, `tmux -V`). These do not modify your system settings.
- **Agent Optimizations**: When launching specific agents (like Gemini), the App may temporarily adjust remote configurations (e.g., `~/.gemini/settings.json`) to match your UI theme. These changes are transient and reverted automatically.
- **Security**: All generated commands are rigorously escaped to prevent injection.

### 5. iCloud Synchronization (Pro Feature)
If you enable iCloud Sync, your server configurations (excluding sensitive passwords/keys unless stored in iCloud Keychain) will be synced across your own devices using **Apple's iCloud service**. We do not have access to this data.

### 6. Contact Us
If you have any questions about this Privacy Policy, please contact us at: atmux-support@saxcave.cc

---

## 繁體中文版

Agentmux（下稱「我們」或「本應用程式」）致力於保護您的隱私。本政策說明了我們處理數據安全與隱私的方法。

### 1. 不收集數據與用戶端獨立運行
Agentmux 是一款專為開發者設計的工具。我們 **不會** 收集、儲存或傳輸您的任何個人資料、伺服器憑據或終端流量至我們的伺服器。所有操作均在您的裝置本地或直接透過 SSH 在您的伺服器上進行。

### 2. 用戶端 AI 橋接（選用）
Agentmux 作為安全的用戶端 SSH 橋接工具，讓您能夠連線到您的遠端伺服器。本 App 本身並不直接提供、託管或運行任何 AI 模型或服務。相反地，它提供橋樑，讓您能與您在自己伺服器上已安裝並配置好的 AI 程式碼助理（如 Claude、Gemini 等）與自訂助理進行互動。
- **處理哪些數據**：當您選擇執行這些助理時，您在終端機與編輯器中輸入的提示詞、指令歷程以及選取的工作區檔案，將會透過您的 SSH 連線傳送，並在您的伺服器上執行代碼任務。
- **傳送至何處**：數據將直接在您的遠端伺服器上，由您使用自己的 API 金鑰所配置的第三方 AI 服務提供商（例如 Anthropic、Google、OpenAI 等）進行處理。
- **無用戶端攔截**：所有數據傳輸皆在您的 SSH 連線中進行點對點安全加密。Agentmux 不會截取、收集、記錄或追蹤任何此類代碼工作區內容或 AI 輸入。使用這些功能即代表您授權將工作區數據傳送至您伺服器上配置的 AI 服務提供商。

### 3. 本地儲存與安全
- **SSH 憑據**：您的密碼與私鑰僅儲存在 iOS 系統的 **Keychain (鑰匙圈)** 中。我們使用 Apple 提供的業界標準加密技術，確保您的憑據安全。
- **伺服器資訊**：所有伺服器設定與專案路徑均透過 **SwiftData** 儲存在您的裝置本地。
- **終端流量**：本應用程式與您的伺服器之間的所有通訊均透過 **SSH 協定** 加密。我們不會截取或記錄您的終端輸出內容。

### 4. 指令透明度與安全
- **自動化探測**：為了提供路徑偵測與 tmux 管理等功能，Agentmux 會執行不具破壞性的探測指令（如 `PATH`、`tmux -V`）。這些指令不會修改您的系統設定。
- **Agent 優化**：啟動特定 Agent（如 Gemini）時，App 可能會暫時調整遠端設定（如 `~/.gemini/settings.json`）以符合您的介面主題。這些變更是暫時性的，並會自動還原。
- **安全性**：所有產生的指令均經過嚴格轉義以防止注入。

### 5. iCloud 同步（專業版功能）
如果您啟用了 iCloud 同步，您的伺服器設定將透過 **Apple 的 iCloud 服務** 在您自己的裝置之間同步。我們無法存取這些數據。

### 6. 聯絡我們
如果您對本隱私政策有疑問，請透過以下方式聯絡我們：atmux-support@saxcave.cc
