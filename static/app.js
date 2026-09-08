document.addEventListener('DOMContentLoaded', () => {
    // --- Global State ---
    let currentQuizData = null;
    let selectedQuizAnswers = {};

    // --- Tab Navigation ---
    const navItems = document.querySelectorAll('.nav-item');
    const tabPages = document.querySelectorAll('.tab-page');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');
            
            navItems.forEach(n => n.classList.remove('active'));
            tabPages.forEach(p => p.classList.remove('active'));
            
            item.classList.add('active');
            const targetEl = document.getElementById(targetTab);
            if (targetEl) {
                targetEl.classList.add('active');
            }

            // Load data when tab opens
            if (targetTab === 'tab-analytics') {
                loadAnalyticsDashboard();
            } else if (targetTab === 'tab-plan') {
                loadCurrentPlan();
            }
        });
    });

    // --- Ingestion Modes (PDF / URL / Text) ---
    const ingestTabs = document.querySelectorAll('.ingest-tab');
    const ingestForms = document.querySelectorAll('.ingest-form');

    ingestTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const mode = tab.getAttribute('data-mode');
            ingestTabs.forEach(t => t.classList.remove('active'));
            ingestForms.forEach(f => f.classList.remove('active'));

            tab.classList.add('active');
            document.getElementById(`ingest-${mode}`).classList.add('active');
        });
    });

    // --- PDF File Ingestion ---
    const dropzone = document.getElementById('pdf-dropzone');
    const pdfInput = document.getElementById('pdf-file-input');
    const uploadPdfBtn = document.getElementById('upload-pdf-btn');

    dropzone.addEventListener('click', () => pdfInput.click());

    pdfInput.addEventListener('change', () => {
        if (pdfInput.files.length > 0) {
            uploadPdfBtn.disabled = false;
            dropzone.querySelector('p').innerHTML = `Selected: <strong>${pdfInput.files[0].name}</strong>`;
        }
    });

    uploadPdfBtn.addEventListener('click', async () => {
        if (!pdfInput.files.length) return;
        const formData = new FormData();
        formData.append('file', pdfInput.files[0]);

        uploadPdfBtn.disabled = true;
        uploadPdfBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Indexing PDF...`;

        try {
            const res = await fetch('/api/materials/pdf', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (res.ok) {
                alert(`Successfully indexed "${data.data.title}" into RAG memory!`);
                pdfInput.value = '';
                dropzone.querySelector('p').innerHTML = `Drag & Drop Study PDF or <span class="browse-link">Browse</span>`;
                loadDocumentsList();
            } else {
                alert(`Error: ${data.detail || 'Failed to process PDF'}`);
            }
        } catch (err) {
            alert(`Error uploading PDF: ${err.message}`);
        } finally {
            uploadPdfBtn.disabled = false;
            uploadPdfBtn.innerHTML = `<i class="fa-solid fa-upload"></i> Upload & Index PDF`;
        }
    });

    // --- URL Ingestion ---
    document.getElementById('upload-url-btn').addEventListener('click', async () => {
        const url = document.getElementById('url-input').value.trim();
        const title = document.getElementById('url-title-input').value.trim();
        if (!url) return alert("Please enter a valid URL");

        const btn = document.getElementById('upload-url-btn');
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Scraping & Indexing...`;

        try {
            const res = await fetch('/api/materials/url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, title })
            });
            const data = await res.json();
            if (res.ok) {
                alert(`Successfully indexed URL into RAG store!`);
                document.getElementById('url-input').value = '';
                document.getElementById('url-title-input').value = '';
                loadDocumentsList();
            } else {
                alert(`Error: ${data.detail}`);
            }
        } catch (err) {
            alert(`Error scraping URL: ${err.message}`);
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-globe"></i> Scrape & Index URL`;
        }
    });

    // --- Raw Text Ingestion ---
    document.getElementById('upload-text-btn').addEventListener('click', async () => {
        const title = document.getElementById('text-title-input').value.trim() || "Notes Entry";
        const content = document.getElementById('text-content-input').value.trim();
        if (!content) return alert("Please enter notes content");

        const btn = document.getElementById('upload-text-btn');
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Indexing Notes...`;

        try {
            const res = await fetch('/api/materials/text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, content })
            });
            const data = await res.json();
            if (res.ok) {
                alert(`Notes indexed into RAG store!`);
                document.getElementById('text-title-input').value = '';
                document.getElementById('text-content-input').value = '';
                loadDocumentsList();
            } else {
                alert(`Error: ${data.detail}`);
            }
        } catch (err) {
            alert(`Error indexing notes: ${err.message}`);
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-file-import"></i> Index Notes`;
        }
    });

    // --- List Documents ---
    async function loadDocumentsList() {
        try {
            const res = await fetch('/api/documents');
            const data = await res.json();
            const container = document.getElementById('materials-list');
            document.getElementById('doc-count').innerText = data.documents.length;

            if (data.documents.length === 0) {
                container.innerHTML = `<p class="empty-msg">No study documents added yet.</p>`;
                return;
            }

            container.innerHTML = data.documents.map(doc => `
                <div class="material-item">
                    <div class="mat-title" title="${doc.title}">${doc.title}</div>
                    <span class="badge badge-${doc.source_type}">${doc.source_type}</span>
                </div>
            `).join('');
        } catch (err) {
            console.error("Error loading documents list", err);
        }
    }

    // --- RAG Grounded Chat ---
    const chatInput = document.getElementById('chat-input');
    const sendChatBtn = document.getElementById('send-chat-btn');
    const chatMessages = document.getElementById('chat-messages');

    sendChatBtn.addEventListener('click', handleSendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });

    async function handleSendMessage() {
        const query = chatInput.value.trim();
        if (!query) return;

        // Append User Message
        appendMessage('user', query);
        chatInput.value = '';

        // Typing indicator
        const loadingId = appendMessage('assistant', '<i class="fa-solid fa-ellipsis fa-pulse"></i> Retrieving RAG context & reasoning...');

        try {
            const res = await fetch('/api/qa', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await res.json();

            // Replace loading message
            removeMessage(loadingId);

            let formattedBubble = formatMarkdown(data.answer);
            
            // Add citations if available
            if (data.citations && data.citations.length > 0) {
                formattedBubble += `
                    <div class="citations-box">
                        <strong><i class="fa-solid fa-bookmark"></i> Grounded Sources:</strong><br>
                        ${data.citations.map(c => `<span class="citation-tag">${c}</span>`).join(' ')}
                    </div>
                `;
            }

            // Audio button for TTS
            const msgObj = appendMessage('assistant', formattedBubble);
            
            const audioBtn = document.createElement('button');
            audioBtn.className = 'audio-btn';
            audioBtn.innerHTML = `<i class="fa-solid fa-volume-high"></i> Listen Explanation`;
            audioBtn.addEventListener('click', () => playAudio(data.answer));
            msgObj.querySelector('.bubble').appendChild(audioBtn);

        } catch (err) {
            removeMessage(loadingId);
            appendMessage('assistant', `Sorry, encountered an error: ${err.message}`);
        }
    }

    function appendMessage(role, htmlContent) {
        const msgDiv = document.createElement('div');
        const id = 'msg-' + Date.now() + Math.random().toString(36).substring(2, 5);
        msgDiv.id = id;
        msgDiv.className = `message ${role}`;
        
        const avatarIcon = role === 'assistant' ? 'fa-robot' : 'fa-user';
        msgDiv.innerHTML = `
            <div class="avatar"><i class="fa-solid ${avatarIcon}"></i></div>
            <div class="bubble">${htmlContent}</div>
        `;

        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return msgDiv;
    }

    function removeMessage(el) {
        if (el && el.parentNode) {
            el.parentNode.removeChild(el);
        }
    }

    // --- Learning Plan Builder ---
    document.getElementById('plan-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const goal = document.getElementById('plan-goal').value.trim();
        const target_date = document.getElementById('plan-duration').value;
        const daily_time = document.getElementById('plan-time').value;
        const level = document.getElementById('plan-level').value;

        const panel = document.getElementById('plan-result-panel');
        panel.innerHTML = `
            <div class="plan-placeholder">
                <i class="fa-solid fa-cog fa-spin placeholder-icon"></i>
                <h3>Synthesizing Step-by-Step Learning Path...</h3>
                <p>Analyzing subject scope, pacing, and learning milestones.</p>
            </div>
        `;

        try {
            const res = await fetch('/api/learning-plan/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal, target_date, daily_time, level })
            });
            const data = await res.json();
            if (res.ok && data.plan) {
                renderLearningPlan(data.plan);
            } else {
                panel.innerHTML = `<p class="empty-msg">Error generating plan: ${data.detail}</p>`;
            }
        } catch (err) {
            panel.innerHTML = `<p class="empty-msg">Error: ${err.message}</p>`;
        }
    });

    async function loadCurrentPlan() {
        try {
            const res = await fetch('/api/learning-plan/current');
            const data = await res.json();
            if (data.plan) {
                renderLearningPlan(data.plan.plan, data.plan.id, data.plan.completed_steps);
            }
        } catch (err) {
            console.error("Error fetching current plan", err);
        }
    }

    function renderLearningPlan(plan, planId = null, completedSteps = []) {
        const panel = document.getElementById('plan-result-panel');
        const pId = planId || plan.id;

        let html = `
            <div class="roadmap-header">
                <h2>${plan.title || 'Structured Study Path'}</h2>
                <p style="color: var(--text-muted); margin-top: 6px;">${plan.overview || ''}</p>
                <div style="margin-top: 12px; font-size: 0.85rem; color: var(--accent-cyan);">
                    <i class="fa-solid fa-clock"></i> Duration: ${plan.total_duration || ''}
                </div>
            </div>
            <div class="timeline">
        `;

        (plan.modules || []).forEach((mod, idx) => {
            const isDone = completedSteps.includes(idx);
            html += `
                <div class="module-card">
                    <h4>${mod.title || `Module ${idx+1}`}</h4>
                    <div class="module-meta"><i class="fa-solid fa-calendar-day"></i> ${mod.timeframe || ''}</div>
                    
                    <div style="font-size: 0.85rem; margin-bottom: 8px;">
                        <strong>Key Objectives:</strong>
                        <ul style="margin-left: 18px; margin-top: 4px;">
                            ${(mod.objectives || []).map(o => `<li>${o}</li>`).join('')}
                        </ul>
                    </div>

                    <div class="task-checklist">
                        <label class="task-item">
                            <input type="checkbox" data-plan-id="${pId}" data-step="${idx}" ${isDone ? 'checked' : ''} class="plan-step-check">
                            <span style="${isDone ? 'text-decoration: line-through; color: var(--text-muted);' : ''}">Complete Module Tasks & Practice Quiz</span>
                        </label>
                    </div>
                </div>
            `;
        });

        html += `</div>`;
        panel.innerHTML = html;

        // Attach step toggle listeners
        panel.querySelectorAll('.plan-step-check').forEach(chk => {
            chk.addEventListener('change', async (e) => {
                const pid = parseInt(e.target.getAttribute('data-plan-id'));
                const stepIdx = parseInt(e.target.getAttribute('data-step'));
                await fetch('/api/learning-plan/toggle-step', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ plan_id: pid, step_index: stepIdx })
                });
                loadCurrentPlan();
            });
        });
    }

    // --- Quiz Arena ---
    document.getElementById('generate-quiz-btn').addEventListener('click', async () => {
        const topic = document.getElementById('quiz-topic').value.trim() || "General Study Review";
        const quiz_type = document.getElementById('quiz-format').value;
        const num_questions = parseInt(document.getElementById('quiz-num').value);

        const container = document.getElementById('quiz-display-area');
        container.innerHTML = `
            <div class="quiz-placeholder">
                <i class="fa-solid fa-spinner fa-spin placeholder-icon"></i>
                <h3>Generating Grounded Quiz Assessment...</h3>
                <p>Extracting key concepts and crafting questions with explanations.</p>
            </div>
        `;

        try {
            const res = await fetch('/api/quiz/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic, num_questions, quiz_type })
            });
            const data = await res.json();
            currentQuizData = data;
            selectedQuizAnswers = {};

            renderActiveQuiz(data);
        } catch (err) {
            container.innerHTML = `<p class="empty-msg">Error launching quiz: ${err.message}</p>`;
        }
    });

    function renderActiveQuiz(quizData) {
        const container = document.getElementById('quiz-display-area');
        const questions = quizData.questions || [];

        if (questions.length === 0) {
            container.innerHTML = `<p class="empty-msg">No questions generated for this topic.</p>`;
            return;
        }

        let html = `
            <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
                <h2><i class="fa-solid fa-file-pen"></i> Quiz: ${quizData.topic}</h2>
                <span class="badge badge-pdf">${questions.length} Questions</span>
            </div>
        `;

        questions.forEach((q, idx) => {
            html += `
                <div class="question-card">
                    <h3>Q${idx+1}. ${q.question}</h3>
                    <div class="options-grid">
                        ${(q.options || []).map(opt => `
                            <button class="option-btn" data-q-id="${q.id}" data-opt="${opt}">
                                ${opt}
                            </button>
                        `).join('')}
                    </div>
                </div>
            `;
        });

        html += `
            <button id="submit-quiz-btn" class="btn btn-primary btn-block" style="margin-top: 20px;">
                <i class="fa-solid fa-check-double"></i> Submit Quiz & Grade Answers
            </button>
        `;

        container.innerHTML = html;

        // Attach option click events
        container.querySelectorAll('.option-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const qId = btn.getAttribute('data-q-id');
                const optVal = btn.getAttribute('data-opt');

                // Clear sibling selection
                btn.parentNode.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');

                selectedQuizAnswers[qId] = optVal;
            });
        });

        // Submit listener
        document.getElementById('submit-quiz-btn').addEventListener('click', async () => {
            try {
                const res = await fetch('/api/quiz/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        quiz_id: currentQuizData.quiz_id,
                        user_answers: selectedQuizAnswers,
                        questions: currentQuizData.questions
                    })
                });
                const evalData = await res.json();
                renderQuizResults(evalData);
            } catch (err) {
                alert(`Error submitting quiz: ${err.message}`);
            }
        });
    }

    function renderQuizResults(evalData) {
        const container = document.getElementById('quiz-display-area');

        let html = `
            <div style="text-align: center; margin-bottom: 28px;">
                <div style="font-size: 3rem; font-family: var(--font-heading); font-weight: 700; color: ${evalData.score_pct >= 70 ? 'var(--accent-green)' : 'var(--accent-amber)'}">
                    ${evalData.score_pct}%
                </div>
                <h3>Quiz Performance Breakdown</h3>
                <p style="color: var(--text-muted);">${evalData.correct_count} out of ${evalData.total_questions} questions answered correctly.</p>
            </div>
        `;

        (evalData.details || []).forEach((d, idx) => {
            const isOk = d.is_correct;
            html += `
                <div class="question-card" style="border-left: 4px solid ${isOk ? 'var(--accent-green)' : 'var(--accent-red)'}">
                    <h3>Q${idx+1}. ${d.question}</h3>
                    <p style="font-size: 0.88rem; margin: 4px 0;"><strong>Your Answer:</strong> ${d.user_answer || '(Unanswered)'} ${isOk ? '✅' : '❌'}</p>
                    ${!isOk ? `<p style="font-size: 0.88rem; color: var(--accent-green);"><strong>Correct Answer:</strong> ${d.correct_answer}</p>` : ''}
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 8px;"><strong>Explanation:</strong> ${d.explanation}</p>
                </div>
            `;
        });

        html += `
            <button id="retry-quiz-btn" class="btn btn-secondary btn-block" style="margin-top: 16px;">
                <i class="fa-solid fa-arrow-rotate-right"></i> Try Another Quiz
            </button>
        `;

        container.innerHTML = html;

        document.getElementById('retry-quiz-btn').addEventListener('click', () => {
            container.innerHTML = `
                <div class="quiz-placeholder">
                    <i class="fa-solid fa-lightbulb placeholder-icon"></i>
                    <h3>Ready to Test Your Comprehension?</h3>
                    <p>Select a topic above or launch a quiz based on your indexed course materials.</p>
                </div>
            `;
        });

        loadAnalyticsDashboard();
    }

    // --- Analytics & Memory Dashboard ---
    async function loadAnalyticsDashboard() {
        try {
            const res = await fetch('/api/student/dashboard');
            const data = await res.json();

            const stats = data.stats || {};
            document.getElementById('stat-docs').innerText = stats.total_documents || 0;
            document.getElementById('stat-quizzes').innerText = stats.total_quizzes_taken || 0;
            document.getElementById('stat-score').innerText = `${stats.average_score || 0}%`;
            document.getElementById('stat-mistakes').innerText = stats.active_mistakes_count || 0;

            // Render Mastery List
            const masteryContainer = document.getElementById('topic-mastery-list');
            const mastery = stats.topic_mastery || [];

            if (mastery.length === 0) {
                masteryContainer.innerHTML = `<p class="empty-msg">Take quizzes to build your topic mastery profile.</p>`;
            } else {
                masteryContainer.innerHTML = mastery.map(m => `
                    <div class="mastery-item">
                        <div class="mastery-meta">
                            <span>${m.topic}</span>
                            <strong>${m.mastery_pct}%</strong>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill" style="width: ${m.mastery_pct}%"></div>
                        </div>
                    </div>
                `).join('');
            }

            // Render Mistakes Bank
            const mistakesContainer = document.getElementById('mistakes-list');
            const mistakes = data.mistakes_bank || [];

            if (mistakes.length === 0) {
                mistakesContainer.innerHTML = `<p class="empty-msg">No missed questions logged yet! Great job.</p>`;
            } else {
                mistakesContainer.innerHTML = mistakes.slice(0, 10).map(mk => `
                    <div class="question-card" style="padding: 12px 16px; margin-bottom: 10px;">
                        <span class="badge badge-pdf">${mk.topic}</span>
                        <p style="font-size: 0.88rem; font-weight: 600; margin-top: 6px;">${mk.question}</p>
                        <p style="font-size: 0.8rem; color: var(--accent-red); margin-top: 4px;">Your Answer: ${mk.user_answer}</p>
                        <p style="font-size: 0.8rem; color: var(--accent-green);">Correct: ${mk.correct_answer}</p>
                    </div>
                `).join('');
            }

        } catch (err) {
            console.error("Error loading analytics", err);
        }
    }

    // --- Audio Player Toast ---
    async function playAudio(text) {
        const toast = document.getElementById('audio-toast');
        const player = document.getElementById('global-audio-player');
        const voice_id = document.getElementById('voice-select').value;

        toast.classList.add('active');
        document.getElementById('audio-toast-title').innerText = "Generating Speech Audio...";

        try {
            const res = await fetch('/api/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, voice_id })
            });

            if (!res.ok) throw new Error("TTS generation failed");

            const blob = await res.blob();
            const audioUrl = URL.createObjectURL(blob);
            player.src = audioUrl;
            document.getElementById('audio-toast-title').innerText = "Playing Audio Explanation";
            player.play();
        } catch (err) {
            document.getElementById('audio-toast-title').innerText = `Speech Error: ${err.message}`;
        }
    }

    document.getElementById('close-toast-btn').addEventListener('click', () => {
        const toast = document.getElementById('audio-toast');
        const player = document.getElementById('global-audio-player');
        player.pause();
        toast.classList.remove('active');
    });

    // Helper Markdown formatting
    function formatMarkdown(text) {
        if (!text) return '';
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n- /g, '<br>• ');
        return formatted;
    }

    // Initialize initial state
    loadDocumentsList();
});
