export const ROBOT_TALK_EVENT = 'robot-talk';

export const emitRobotTalk = (detail) => {
  if (typeof window === 'undefined') return;
  const payload = typeof detail === 'string' ? { text: detail } : detail;
  window.dispatchEvent(new CustomEvent(ROBOT_TALK_EVENT, { detail: payload }));
};

export const onRobotTalk = (handler) => {
  if (typeof window === 'undefined') return () => {};
  const listener = (event) => handler(event.detail || {});
  window.addEventListener(ROBOT_TALK_EVENT, listener);
  return () => window.removeEventListener(ROBOT_TALK_EVENT, listener);
};
