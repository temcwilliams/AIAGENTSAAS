'use strict';
class RelayVoiceController{
  constructor({Recognition,synthesis,Utterance,send,canStart=()=>true,onState=()=>{},onStop=()=>{},language='en-US',readAloud=()=>true,isVisible=()=>true,timer=setTimeout,clearTimer=clearTimeout}){Object.assign(this,{Recognition,synthesis,Utterance,send,canStart,onState,onStop,language,readAloud,isVisible,timer,clearTimer});this.active=false;this.generation=0;this.recognition=null;this.deadline=null}
  state(message){this.onState(message,this.active)}
  start(){if(this.active)return;if(!this.Recognition){this.state('Voice input is unavailable in this browser. Use keyboard dictation or open Relay in Safari or Chrome.');return}if(!this.isVisible()){this.state('Open Relay before starting voice.');return}try{if(!this.canStart())return}catch(error){this.state(error.message);return}this.active=true;this.generation++;this.listen(this.generation)}
  stop(message='Voice stopped. Microphone off.'){this.active=false;this.generation++;this.clearTimer(this.deadline);this.deadline=null;const recognition=this.recognition;this.recognition=null;try{recognition?.abort()}catch{}this.synthesis?.cancel();this.onStop();this.state(message)}
  valid(id){return this.active&&id===this.generation&&this.isVisible()}
  listen(id){if(!this.valid(id))return;let text='';let recognition;try{recognition=new this.Recognition()}catch{this.stop('Voice recognition could not be initialized in this browser.');return}this.recognition=recognition;recognition.lang=this.language;recognition.continuous=false;recognition.interimResults=false;
    recognition.onresult=event=>{if(!this.valid(id)||this.recognition!==recognition)return;for(let i=event.resultIndex||0;i<event.results.length;i++){if(event.results[i].isFinal!==false)text+=event.results[i][0].transcript+' '}};
    recognition.onerror=event=>{if(!this.valid(id)||this.recognition!==recognition)return;this.stop(event.error==='not-allowed'?'Microphone or speech permission denied. Check browser settings, then tap Start again.':'Voice stopped: '+event.error+'. Tap Start to try again.')};
    recognition.onend=async()=>{if(!this.valid(id)||this.recognition!==recognition)return;this.recognition=null;this.clearTimer(this.deadline);text=text.trim().slice(0,8000);if(!text){this.stop('No speech detected. Tap Start to try again.');return}this.state('Thinking…');try{const reply=await this.send(text);if(!this.valid(id))return;if(!reply)throw Error('No completed reply. Check the chat or server connection.');if(this.readAloud()&&this.synthesis&&this.Utterance){const utterance=new this.Utterance(String(reply).slice(0,6000));utterance.lang=this.language;utterance.onend=()=>{if(this.valid(id))this.listen(id)};utterance.onerror=()=>{if(this.valid(id))this.stop('Spoken playback was interrupted. Tap Start to continue.')};this.state('Speaking…');this.synthesis.speak(utterance)}else this.listen(id)}catch(error){if(this.valid(id))this.stop(error.message)}};
    this.state('Listening… Speak, then pause to send.');try{recognition.start();this.deadline=this.timer(()=>{if(this.valid(id)&&this.recognition===recognition)this.stop('Listening timed out. Tap Start to continue.')},60000)}catch{this.stop('This browser could not start voice. Try keyboard dictation or tap Start again.')}
  }
}
if(typeof module!=='undefined')module.exports={RelayVoiceController};
if(typeof document!=='undefined'){
  const readback=document.getElementById('readAloud');readback.checked=preferences.get().readAloud;readback.onchange=()=>preferences.set({readAloud:readback.checked});
  relayVoice=new RelayVoiceController({Recognition:window.SpeechRecognition||window.webkitSpeechRecognition,synthesis:window.speechSynthesis,Utterance:window.SpeechSynthesisUtterance,language:navigator.language||'en-US',isVisible:()=>!document.hidden,readAloud:()=>readback.checked,
    canStart(){if(typeof playwrightEnabled!=='undefined'&&playwrightEnabled)throw Error('Use typed requests with Playwright so you can review browser tool approvals.');if(busy||connecting)throw Error('Finish the current reply or connection check first.');if(!models.length)throw Error('Connect your Ollama server before starting voice.');if($('input').value.trim())throw Error('Send or clear your draft before starting voice.');return true},
    async send(text){if(busy||connecting)throw Error('The workspace is busy. Tap Start when ready.');if($('input').value.trim())throw Error('Your typed draft was kept. Send or clear it before using voice again.');voiceSending=true;try{$('input').value=text;return await $('composer').onsubmit({preventDefault(){}})}finally{voiceSending=false}},
    onStop(){if(voiceSending&&busy)controller.abort()},
    onState(message,active){$('voiceStatus').textContent=message;$('voiceToggle').textContent=active?'Stop voice':'Start voice';$('voiceToggle').setAttribute('aria-pressed',String(active));$('voiceNav').textContent=active?'◉ Voice active':'◉ Voice conversation'}
  });
  $('voiceNav').onclick=()=>{if(relayVoice.active){relayVoice.stop();return}openDialog($('voiceGuide'));setSidebar(false)};
  $('closeVoiceGuide').onclick=()=>closeDialog($('voiceGuide'));
  $('voiceToggle').onclick=()=>{if(relayVoice.active)relayVoice.stop();else openDialog($('voiceGuide'))};
  $('voiceStart').onclick=()=>{closeDialog($('voiceGuide'));relayVoice.start()};
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&relayVoice.active)relayVoice.stop('Voice stopped because Relay left the foreground. Reopen Relay and tap Start.')});
  window.addEventListener('pagehide',()=>relayVoice.stop());
  $('cookieInfo').onclick=()=>openDialog($('privacyGuide'));$('closePrivacyGuide').onclick=()=>closeDialog($('privacyGuide'));
  $('clearPreferences').onclick=()=>{preferences.set({theme:'dark',mode:'chat',chatModel:'',codingModel:'',readAloud:true});if(typeof applyTheme==='function')applyTheme('dark');readback.checked=true;toast('Preference cookie reset. Chat history and server settings were kept.')};
}
