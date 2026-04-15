import React, { useEffect, useMemo, useRef, useState } from 'react';
import './SideEmoRobot.css';
import { onRobotTalk } from '../utils/robotTalk';

const SideEmoRobot = () => {
  const phrases = useMemo(
    () => [
      '我在这儿，随时等你。',
      '要不要我帮你找找？',
      '你忙你的，我帮你盯着状态。',
      '今天系统很安静哦。',
      '刚刚看了下，一切正常。',
      '想查谁就告诉我。',
      '导入完别忘了拼音转换，和数据写入哦，记得去热词配置写入热词哦，我会提醒你。',
      '如果卡住了，喊我一声。',
      '我会一直守在这里。',
      '你一开口，我就醒。',
      '别急，我们慢慢来。',
      '需要提示的话，我随时说两句。',
    ],
    []
  );

  const [phrase, setPhrase] = useState('');
  const [show, setShow] = useState(false);
  const [isSleep, setIsSleep] = useState(false);
  const hideTimerRef = useRef(null);
  const randomTimerRef = useRef(null);
  const idleTimerRef = useRef(null);
  const lastActiveRef = useRef(Date.now());

  const showPhrase = (text) => {
    if (!text) return;
    setPhrase(text);
    setShow(true);
    setIsSleep(false);
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
    }
    hideTimerRef.current = setTimeout(() => {
      setShow(false);
    }, 4200);
  };

  useEffect(() => {
    const scheduleRandom = () => {
      const delay = 15000 + Math.random() * 10000;
      randomTimerRef.current = setTimeout(() => {
        const next = phrases[Math.floor(Math.random() * phrases.length)];
        if (!isSleep) {
          showPhrase(next);
        }
        scheduleRandom();
      }, delay);
    };

    scheduleRandom();
    const unsubscribe = onRobotTalk((detail) => {
      const text = typeof detail === 'string' ? detail : detail?.text;
      showPhrase(text);
    });

    const markActive = () => {
      lastActiveRef.current = Date.now();
      if (isSleep) {
        setIsSleep(false);
      }
    };

    const activityEvents = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
    activityEvents.forEach((evt) => window.addEventListener(evt, markActive, { passive: true }));

    idleTimerRef.current = setInterval(() => {
      const threshold = 60 * 1000;
      if (Date.now() - lastActiveRef.current >= threshold) {
        setIsSleep(true);
      }
    }, 5000);

    return () => {
      if (randomTimerRef.current) {
        clearTimeout(randomTimerRef.current);
      }
      if (hideTimerRef.current) {
        clearTimeout(hideTimerRef.current);
      }
      if (idleTimerRef.current) {
        clearInterval(idleTimerRef.current);
      }
      activityEvents.forEach((evt) => window.removeEventListener(evt, markActive));
      unsubscribe();
    };
  }, [phrases, isSleep]);

  return (
    <div className="side-emo-anchor">
      <div className={`side-emo-bubble ${show ? 'is-show' : ''}`}>
        {phrase}
      </div>
      <div className={`side-emo-robot ${show ? 'is-smile' : ''} ${isSleep ? 'is-sleep' : ''}`}>
        <div className="side-emo-headphone-band" />
        <div className="side-emo-earcup left">
          <div className="side-emo-mic-arm">
            <div className="side-emo-mic-head" />
          </div>
        </div>
        <div className="side-emo-earcup right" />

        <div className="side-emo-head">
          <div className="side-emo-face">
            <div className="side-emo-eyes">
              <span className="side-emo-eye" />
              <span className="side-emo-eye" />
            </div>
            <div className="side-emo-zzz">Zzz</div>
          </div>
        </div>

        <div className="side-emo-leg left" />
        <div className="side-emo-leg right" />
        <div className="side-emo-skate" />
      </div>
    </div>
  );
};

export default SideEmoRobot;
