import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth, useLanguage, useAppData } from '../context/AppContext';
import { LayoutWrapper } from '../components/layout/LayoutWrapper';
import { ChatMessage } from '../components/chat/ChatMessage';
import { ChatInput } from '../components/chat/ChatInput';
import { SuggestionChip } from '../components/chat/SuggestionChip';
import { LoadingIndicator } from '../components/common/LoadingIndicator';
import { chatService } from '../services/chatService';
import { Logo } from '../components/common/Logo';
// Added Volume2 icon for the Read Aloud button
import { MessageSquare, ArrowRight, CornerDownLeft, Sparkles, QrCode, Volume2 } from 'lucide-react';

export const Chat = () => {
  const { t, language } = useLanguage();
  const { isGuest } = useAuth();
  const { chatHistory, addChatMessage, createNewChat } = useAppData();
  const location = useLocation();
  const [activeChatId, setActiveChatId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const chatEndRef = useRef(null);
  const audioRef = useRef(null);

  const suggestionChips = [
    { label: "Cooperative Registration", category: "Registration" },
    { label: "Member Rights", category: "Membership" },
    { label: "Committee Management", category: "Governance" },
    { label: "Legal Procedures", category: "Governance" },
    { label: "Required Documents", category: "Registration" },
    { label: "Dispute Resolution", category: "Dispute Resolution" }
  ];

  const activeChat = chatHistory.find(c => c.id === activeChatId);
  const messages = activeChat ? activeChat.messages : [];

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  useEffect(() => {
    if (location.state?.resumeChatId) {
      setActiveChatId(location.state.resumeChatId);
    } else if (location.state?.initialQuery) {
      handleInitialQuery(location.state.initialQuery, location.state.initialCategory);
    }
  }, [location.state]);

  // NEW STANDALONE AUDIO FUNCTION: Can be triggered by button or voice chat
  const playReadAloud = async (textToRead) => {
    if (!textToRead) return;
    setIsPlayingAudio(true);
    try {
      console.log("[TTS] Sending answer to /voice/speak...");
      const ttsResponse = await fetch("https://sahakar-sahayak-4.onrender.com/voice/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: textToRead, language: language })
      });

      if (!ttsResponse.ok) {
        const errorText = await ttsResponse.text();
        throw new Error(`TTS failed: ${ttsResponse.status} ${errorText}`);
      }

      const ttsData = await ttsResponse.json();
      console.log("[TTS] Audio received");

      if (ttsData.audio) {
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
        }
        const audio = new Audio(`data:audio/mp3;base64,${ttsData.audio}`);
        audioRef.current = audio;
        
        audio.onended = () => {
          setIsPlayingAudio(false);
        };

        await audio.play();
      }
    } catch (ttsError) {
      console.error("[TTS] Error:", ttsError);
      setIsPlayingAudio(false);
    }
  };

  const handleInitialQuery = async (queryText, category) => {
    setIsLoading(true);
    const userMsg = {
      sender: 'user',
      text: queryText,
      time: new Date().toISOString()
    };
    const chatId = createNewChat(queryText, category || "General", userMsg);
    setActiveChatId(chatId);

    try {
      const response = await chatService.sendMessage(queryText, language, chatId);
      const assistantMsg = {
        sender: 'assistant',
        text: response.answer,
        time: new Date().toISOString(),
        steps: response.steps,
        notes: response.notes,
        provisions: response.provisions,
        documents: response.documents,
        sources: response.sources,
        suggestedQuestions: response.suggestedQuestions,
        action_url: response.action_url,
        qr_code_base64: response.qr_code_base64
      };
      addChatMessage(chatId, assistantMsg);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (text, file, isVoice = false) => {
    let chatId = activeChatId;
    const userMsgText = text || (file ? `Attached Document: ${file.name}` : "");
    const userMsg = {
      sender: 'user',
      text: userMsgText,
      time: new Date().toISOString()
    };

    setIsLoading(true);

    if (!chatId) {
      chatId = createNewChat(
        text ? text.slice(0, 30) + "..." : "File Upload",
        "General",
        userMsg
      );
      setActiveChatId(chatId);
    } else {
      addChatMessage(chatId, userMsg);
    }

    try {
      const response = await chatService.sendMessage(userMsgText, language, chatId);

      const assistantMsg = {
        sender: 'assistant',
        text: response.answer,
        time: new Date().toISOString(),
        steps: response.steps,
        notes: response.notes,
        provisions: response.provisions,
        documents: response.documents,
        sources: response.sources,
        suggestedQuestions: response.suggestedQuestions,
        action_url: response.action_url,
        qr_code_base64: response.qr_code_base64
      };

      addChatMessage(chatId, assistantMsg);

      // Trigger auto-play only if the user spoke to the bot
      if (isVoice && response.answer && response.answer.trim()) {
        playReadAloud(response.answer);
      }
    } catch (err) {
      console.error("[CHAT] Error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChipClick = (queryText, category) => {
    handleSendMessage(queryText, null);
  };

  const lastMsg = messages[messages.length - 1];
  const followUpQuestions = lastMsg && lastMsg.sender === 'assistant' && lastMsg.suggestedQuestions
    ? lastMsg.suggestedQuestions
    : [];

  return (
    <LayoutWrapper title={t('askSahayak')}>
      <div className="flex flex-col relative h-[calc(100vh-8.5rem)] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl overflow-hidden shadow-sm transition-colors">
        
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="max-w-xl mx-auto text-center py-8 space-y-6 animate-message-appear">
              <div className="h-16 w-16 bg-primary-50 dark:bg-primary-950/40 rounded-2xl flex items-center justify-center text-primary-600 dark:text-primary-400 mx-auto shadow-sm border border-primary-100/40">
                <Sparkles className="h-8 w-8 text-primary-600 dark:text-primary-400 animate-pulse-subtle" />
              </div>
              <div className="space-y-3">
                <h2 className="text-lg sm:text-xl font-black font-display text-slate-855 dark:text-white">
                  {t('askSahayak')}
                </h2>
                <div className="p-4 bg-slate-50 dark:bg-slate-950 rounded-2xl border border-slate-200/60 dark:border-slate-850 text-xs sm:text-sm text-slate-650 dark:text-slate-300 leading-relaxed max-w-lg mx-auto">
                  {t('chatInitialGreeting')}
                </div>
              </div>
              <div className="space-y-3">
                <p className="text-[10px] sm:text-xs font-bold text-slate-450 dark:text-slate-550 uppercase tracking-wider">
                  Select a topic to start
                </p>
                <div className="flex flex-wrap gap-2.5 justify-center max-w-lg mx-auto">
                  {suggestionChips.map((chip, idx) => (
                    <SuggestionChip
                      key={idx}
                      label={chip.label}
                      onClick={() => handleChipClick(chip.label, chip.category)}
                    />
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto">
              {messages.map((msg, idx) => (
                <div key={idx} className="mb-4">
                  <ChatMessage
                    message={msg}
                    conversationCategory={activeChat?.category || "General"}
                  />
                  
                  {msg.sender === 'assistant' && (
                    <div className="flex flex-col items-start mt-3 sm:ml-12 pl-4">
                      
                      {/* NEW BUTTON: Read Aloud Trigger */}
                      <button
                        onClick={() => playReadAloud(msg.text)}
                        disabled={isPlayingAudio}
                        className="mb-3 flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 dark:text-blue-300 rounded-full text-xs font-bold transition-colors shadow-sm disabled:opacity-50"
                      >
                        <Volume2 className="h-3.5 w-3.5" />
                        {isPlayingAudio ? "Playing Voice..." : "Read Aloud"}
                      </button>

                      {/* HIGHLY VISIBLE GREEN CITATION & QR CODE BLOCK */}
                      {(msg.sources?.length > 0 || msg.qr_code_base64) && (
                        <div className="border-l-4 border-emerald-500 bg-emerald-50/50 dark:bg-emerald-900/10 p-4 rounded-r-lg shadow-sm w-full max-w-sm">
                          
                          {msg.sources && msg.sources.length > 0 && (
                            <div className="mb-4">
                              <p className="text-[11px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-widest mb-1">
                                Verified Official Source
                              </p>
                              <p className="text-sm text-slate-800 dark:text-slate-200 font-semibold flex items-center gap-2">
                                📄 {msg.sources[0].documentName} {msg.sources[0].provision ? `(${msg.sources[0].provision})` : ''}
                              </p>
                            </div>
                          )}
                          
                          {msg.qr_code_base64 && (
                            <div className="mt-1 p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl flex flex-col items-center gap-2 shadow-sm">
                              <p className="text-[12px] font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5 uppercase tracking-wide">
                                <QrCode className="h-4 w-4 text-emerald-600" />
                                Scan for WhatsApp Receipt
                              </p>
                              <img 
                                src={`data:image/png;base64,${msg.qr_code_base64}`} 
                                alt="WhatsApp QR Code" 
                                className="w-36 h-36 rounded-lg shadow-sm border border-slate-200 bg-white p-1"
                              />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="flex gap-4 mb-6">
                  <div className="h-9 w-9 rounded-xl bg-primary-100 dark:bg-primary-950 flex items-center justify-center shrink-0 border border-primary-200/40">
                    <Logo className="h-5 w-5" />
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-2xl p-4 shrink-0">
                    <LoadingIndicator text={t('chatPreparingAnswer')} />
                  </div>
                </div>
              )}

              {!isLoading && followUpQuestions.length > 0 && (
                <div className="mt-4 flex flex-col gap-2 text-left pl-12 animate-message-appear">
                  <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                    <CornerDownLeft className="h-3.5 w-3.5" />
                    {t('suggestedQuestions')}
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {followUpQuestions.map((q, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleChipClick(q, activeChat?.category)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 hover:bg-emerald-50 dark:bg-slate-950 dark:hover:bg-emerald-950/20 text-[11px] font-semibold text-slate-600 hover:text-emerald-700 dark:text-slate-450 dark:hover:text-emerald-450 border border-slate-200 hover:border-emerald-200 dark:border-slate-800 dark:hover:border-emerald-900/50 rounded-full transition-colors text-left"
                      >
                        <span>{q}</span>
                        <ArrowRight className="h-3 w-3 shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          )}
        </div>

        {isPlayingAudio && (
          <div className="absolute bottom-[85px] w-full flex justify-center z-50 pointer-events-none">
            <button
              onClick={() => {
                if (audioRef.current) {
                  audioRef.current.pause();
                  setIsPlayingAudio(false);
                }
              }}
              className="pointer-events-auto flex items-center gap-3 bg-red-600 hover:bg-red-700 text-white text-sm font-extrabold px-6 py-3 rounded-full shadow-2xl border-2 border-white transition-all transform hover:scale-105"
            >
              <div className="w-3.5 h-3.5 bg-white rounded-sm animate-pulse"></div>
              STOP SPEAKING
            </button>
          </div>
        )}

        <ChatInput onSend={handleSendMessage} isLoading={isLoading} />
      </div>
    </LayoutWrapper>
  );
};

export default Chat;