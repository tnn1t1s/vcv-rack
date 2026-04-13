#pragma once
// AIModule.hpp — base class for llama.cpp-driven VCV Rack modules.
//
// Handles the full llama.cpp lifecycle: model load (background thread),
// inference thread with prompt/result exchange, and patch serialization.
//
// Subclass contract:
//   virtual std::string buildPrompt()                    — called to generate inference input
//   virtual void handleResult(const std::string& resp)  — called when inference completes
//
// Typical subclass usage:
//   1. At end of constructor: startInferenceThread()
//   2. In process(): call submitPrompt(buildPrompt()) on a timer
//   3. In process(): call pollResult() and dispatch to handleResult()

// ── llama.h must come before rack.hpp to avoid DEPRECATED macro collision ───
#ifdef DEPRECATED
#undef DEPRECATED
#endif
#include "llama.h"

#include <rack.hpp>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <string>
#include <vector>

#include "../AgentModule.hpp"

// Initialise llama backend once per process lifetime.
static inline void ensureLlamaBackend() {
    static bool done = false;
    if (!done) { done = true; llama_backend_init(); }
}

// ─────────────────────────────────────────────────────────────────────────────

struct AIModule : AgentModule {

    enum class ModelState { UNLOADED, LOADING, READY, ERROR };

    // Readable from any thread (atomic)
    std::atomic<ModelState> modelState{ModelState::UNLOADED};
    std::string             modelPath;
    std::string             modelError;   // set on ERROR

    // ── Subclass interface ────────────────────────────────────────────────────

    virtual std::string buildPrompt()                        = 0;
    virtual void        handleResult(const std::string& r)  = 0;

    // ── API ───────────────────────────────────────────────────────────────────

    // Load model from path (GUI thread — non-blocking, loads in background).
    void loadModel(const std::string& path) {
        ensureLlamaBackend();
        modelPath  = path;
        modelState = ModelState::LOADING;
        modelError = "";

        std::thread([this]() {
            llama_model_params mp = llama_model_default_params();
            mp.n_gpu_layers = 99;  // offload all layers to Metal when available

            struct llama_model* m = llama_model_load_from_file(modelPath.c_str(), mp);
            if (!m) {
                modelError = "Could not load: " + modelPath;
                modelState = ModelState::ERROR;
                return;
            }

            llama_context_params cp = llama_context_default_params();
            cp.n_ctx     = 2048;
            cp.n_threads = 4;
            cp.n_batch   = 512;

            struct llama_context* c = llama_init_from_model(m, cp);
            if (!c) {
                llama_model_free(m);
                modelError = "Could not create context";
                modelState = ModelState::ERROR;
                return;
            }

            {
                std::lock_guard<std::mutex> lk(llamaMutex_);
                if (llamaCtx_)   { llama_free(llamaCtx_);       llamaCtx_   = nullptr; }
                if (llamaModel_) { llama_model_free(llamaModel_); llamaModel_ = nullptr; }
                llamaModel_ = m;
                llamaCtx_   = c;
            }
            modelState = ModelState::READY;
        }).detach();
    }

    // Submit prompt for inference (audio thread). Drops silently if thread busy.
    void submitPrompt(const std::string& prompt) {
        std::unique_lock<std::mutex> lk(promptMutex_, std::try_to_lock);
        if (!lk.owns_lock()) return;
        pendingPrompt_ = prompt;
        promptReady_   = true;
        promptCV_.notify_one();
    }

    // Check for a completed result (audio thread). Returns true once per result.
    bool pollResult(std::string& out) {
        if (!resultReady_.load()) return false;
        std::lock_guard<std::mutex> lk(resultMutex_);
        out          = lastResult_;
        resultReady_ = false;
        return true;
    }

    // Call once at end of subclass constructor.
    void startInferenceThread() {
        stopThread_ = false;
        inferThread_ = std::thread([this]() {
            while (!stopThread_.load()) {
                std::unique_lock<std::mutex> lk(promptMutex_);
                promptCV_.wait(lk, [this]{
                    return promptReady_ || stopThread_.load();
                });
                if (stopThread_.load()) break;

                std::string prompt  = pendingPrompt_;
                promptReady_        = false;
                lk.unlock();

                std::string result;
                {
                    std::lock_guard<std::mutex> mlk(llamaMutex_);
                    if (llamaModel_ && llamaCtx_)
                        result = runInference_(prompt);
                }

                {
                    std::lock_guard<std::mutex> rlk(resultMutex_);
                    lastResult_  = result;
                    resultReady_ = true;
                }
            }
        });
    }

    // ── Serialization ─────────────────────────────────────────────────────────

    json_t* dataToJson() override {
        json_t* root = json_object();
        if (!modelPath.empty())
            json_object_set_new(root, "modelPath", json_string(modelPath.c_str()));
        return root;
    }

    void dataFromJson(json_t* root) override {
        json_t* j = json_object_get(root, "modelPath");
        if (j && json_is_string(j)) {
            const char* p = json_string_value(j);
            if (p && p[0]) loadModel(std::string(p));
        }
    }

    // ── Destructor ────────────────────────────────────────────────────────────

    ~AIModule() {
        stopThread_ = true;
        promptCV_.notify_all();
        if (inferThread_.joinable()) inferThread_.join();

        std::lock_guard<std::mutex> lk(llamaMutex_);
        if (llamaCtx_)   { llama_free(llamaCtx_);        llamaCtx_   = nullptr; }
        if (llamaModel_) { llama_model_free(llamaModel_); llamaModel_ = nullptr; }
    }

private:
    // llama objects — owned/modified only under llamaMutex_ or from inference thread
    std::mutex     llamaMutex_;
    struct llama_model*   llamaModel_ = nullptr;
    struct llama_context* llamaCtx_   = nullptr;

    // Inference thread
    std::thread             inferThread_;
    std::atomic<bool>       stopThread_{false};

    std::mutex              promptMutex_;
    std::condition_variable promptCV_;
    std::string             pendingPrompt_;
    bool                    promptReady_ = false;

    std::mutex              resultMutex_;
    std::string             lastResult_;
    std::atomic<bool>       resultReady_{false};

    // Apply the model's built-in chat template to a user message.
    // Returns the fully-formatted string ready for tokenization.
    std::string applyChatTemplate_(const std::string& userMessage) {
        llama_chat_message msgs[1] = {{ "user", userMessage.c_str() }};
        // First call: measure required buffer size
        int needed = llama_chat_apply_template(nullptr,
                                               msgs, 1,
                                               true,   // add_ass: append model-turn prefix
                                               nullptr, 0);
        if (needed <= 0) return userMessage;  // fallback: use raw text
        std::vector<char> buf((size_t)needed + 1, '\0');
        llama_chat_apply_template(nullptr,
                                  msgs, 1,
                                  true,
                                  buf.data(), (int)buf.size());
        return std::string(buf.data(), (size_t)needed);
    }

    // Synchronous inference — call only from inference thread under llamaMutex_.
    std::string runInference_(const std::string& prompt) {
        // Apply chat template so instruction-tuned models follow the prompt correctly
        std::string formatted = applyChatTemplate_(prompt);

        // Clear KV memory for a fresh decode pass
        llama_memory_t mem = llama_get_memory(llamaCtx_);
        llama_memory_clear(mem, true);

        // Tokenize
        const llama_vocab* vocab_ = llama_model_get_vocab(llamaModel_);
        std::vector<llama_token> toks(2048);
        int n = llama_tokenize(vocab_,
                               formatted.c_str(), (int)formatted.size(),
                               toks.data(), (int)toks.size(),
                               true, false);
        if (n <= 0) return "";
        toks.resize((size_t)n);

        // Prefill
        llama_batch batch = llama_batch_get_one(toks.data(), n);
        if (llama_decode(llamaCtx_, batch) != 0) return "";

        // Sample greedily until EOG or max tokens
        const llama_vocab*         vocab  = vocab_;
        llama_sampler_chain_params sp     = llama_sampler_chain_default_params();
        llama_sampler*             smpl   = llama_sampler_chain_init(sp);
        llama_sampler_chain_add(smpl, llama_sampler_init_greedy());

        std::string result;
        static constexpr int MAX_NEW = 128;
        for (int i = 0; i < MAX_NEW; ++i) {
            llama_token tok = llama_sampler_sample(smpl, llamaCtx_, -1);
            if (llama_vocab_is_eog(vocab, tok)) break;

            char buf[256] = {};
            int  len = llama_token_to_piece(vocab_, tok,
                                            buf, (int)sizeof(buf) - 1, 0, false);
            if (len > 0) result.append(buf, (size_t)len);

            llama_batch next = llama_batch_get_one(&tok, 1);
            if (llama_decode(llamaCtx_, next) != 0) break;
        }

        llama_sampler_free(smpl);
        return result;
    }
};
