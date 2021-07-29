# Voice-Assistance
code of speech recognization using library(Chatter Bot) 
from chatterbot import ChatBot 
from chatterbot.trainers import ListTrainer
import speech_recognition as sr
import pyttsx3
mybot = ChatBot('Sravs')
r = sr.Recognizer()
sensy = pyttsx3.init()

mycoversation = ['Hello',
                 'Hi',
                 'How are you',
                 'Am fine',
                 'How do u do',
                 'What is your name',
                 'Dont u know me,  i am sravs Tron Mans AI companion']
trainer = ListTrainer(mybot)
tariner.train(myconversation)
while True:
    with sr.Microphone() as source:
        print("Speak:")
        audio = r.listen(source)
    try:
        text = r.recognize_google(audio)
        print("You said"*text)
        bot_response = mybot.get_response(text)
        print("bots response",bot_response)
        alexa.say(str(bot_response))
        alexa.runAndwait()
    except sr.UnknownValueError:
        print("Couldnnot understand audio")
    except sr.RequestError as e:
        print("could not request results;{0}".format(e))

