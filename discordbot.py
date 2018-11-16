import discord
import asyncio
import os
import matplotlib
import dropbox
import random
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from pathlib import Path

fontprop = FontProperties(fname='.fonts/ipaexg.ttf', size=10)

TOKEN = "トークンを入力"
DROPBOXTOKEN = "Dropbox用トークンを入力"
GRAPHPATH = "graph/"
SAVEPATH = "save/"
OTHERSPATH = "others/"
DBX_SPATH = "/save/"
DBX_OPATH = "/others/"
Commands = ["add", "help", "cancel", "myrate", "team", "history", "graph", "save", "restore", "reset", "manager", "add2", "getfile", "backup", "download", "del" ]
Commands_Zaihou = ["財宝", "時間設定"]

# 管理者一覧
Managers = ["管理者のID"]
# オーナーid
Owner = "管理者のID"
# エラーコード
ERRORCODE = {1: "正常に実行されました．", 100: "入力が空．", 200: "指定された名前のコマンドが存在しない．", 310: "addコマンドの引数の数がおかしい．", 320:"addコマンドの第一引数には数値を入力してください．", 330: "ユーザーが見つかりません．", 340: "managerコマンドではメンションをしてください．",  350: "add2コマンドの引数の数がおかしい．", 360: "add2コマンドではメンションをしてください．", 370: "add2コマンドでは数値を渡してください．", 400: "引数の数がおかしい．"}

client = discord.Client()
dbx = dropbox.Dropbox(DROPBOXTOKEN)
dbx.users_get_current_account()
act_bef = []
count = 0

class Team:
    members = {} # メンバーオブジェクトはディクショナリで管理, key が id
    names = {} # keyが id, 表示用の名前を管理
    rates = {} # key が id, それぞれが持つレートを管理

    def __init__(self):
        self.rate = 0

    def addRate(self, rate, id, time, name):
        if not id in self.members.keys(): # メンバー追加
            newMember = Member(id)
            self.members[id] = newMember
            self.names[id] = name
        return self.members[id].add(rate, time)

    def cancel(self, id):
        self.members[id].cancel()

    def getMemRate(self, id):
        rate = 0
        if id in self.members.keys():
            rate = self.members[id].getMyRate()
        return rate

    def update(self):
        self.rate = 0
        self.rates = {}
        for key in self.members.keys():
            self.rates[key] = self.members[key].rate_sum
            self.rate += self.members[key].rate_sum

    def getHistory(self, id):
        message = "履歴なし"
        if id in self.members.keys():
            message = self.members[id].getHistory()
        return message

    def getTeamRate(self):
        self.update()
        return self.rate

    def getTeamInfo(self):
        self.update()
        sortedList = sorted(self.rates.items(), key=lambda x: -x[1])

        message = "チームレート: " + str(self.rate) + "\n"
        for pare in sortedList: # pare[0]が key, pare[1]が value
            if isManager(pare[0]):
                message = message + "[管]"
            message = message + "[" + self.names[pare[0]] + "] " + str( self.rates[pare[0]] ) + "\n"
        return message

    def createGraph(self):
        plt.style.use('ggplot')
        self.update()
        sortedList = sorted(self.rates.items(), key=lambda x: -x[1])

        X = []
        Y = []
        names = []

        for i in range(len(sortedList)):
            X.append(i)
            Y.append(sortedList[i][1])
            names.append(self.names[sortedList[i][0]])

        plt.bar(X,Y, align="center")
        plt.xticks(X, names, font_properties=fontprop)
        plt.savefig(GRAPHPATH + "graph.png")

    def save(self, message):
        for key in self.members.keys():
            savedata = key + "\n" + self.names[key] + "\n"
            for history in reversed(self.members[key].rate_history):
                savedata = savedata + str(history[0]) + "," + str(history[1]) + "\n"
            if not os.path.exists(SAVEPATH):
                os.makedirs(SAVEPATH, exist_ok=True)
            f = open( SAVEPATH + key + ".txt" , mode="w" )
            f.write(savedata)
            f.close()
        printSysMessage("レート情報を保存しました．")

    def restore(self):
        self.members = {}
        self.names = {}
        self.rates = {}
        p = Path( SAVEPATH )
        files = list(p.glob("*.txt"))
        for file in files:
            f = open( str(file), mode="r" )
            history = f.readlines()
            history[0] = history[0].replace("\n", "")
            history[1] = history[1].replace("\n", "")
            if history[0] in self.members.keys():
                self.members[history[0]].reset()
            for i in range( 2, len(history) ):
                tmp = history[i].split(",")
                if len(tmp) > 2:
                    tmp[2].replace("\n", "")
                    self.addRate( int_original( tmp[0] ), history[0], tmp[1] + "," +  tmp[2], history[1] )
            f.close()
        printSysMessage("レート情報を復元しました．")

    def reset(self):
        for member in self.members.values():
            member.reset()

    def delMember( self, id ):
        self.members.pop( str(id) )
        name = self.names.pop( str(id) )
        self.rates.pop( str(id) )
        try :
            dbx.files_delete( DBX_SPATH + str( id ) + ".txt" )
        except :
            printSysMessage( "Del Failed" )
        return name

class Member:
    rate_history = [] # Addするたびに，追加された日とレートの組み合わせ(リスト)が追加

    def __init__(self, id):
        self.id = id
        self.rate_history = []
        self.time_s = "16"
        self.time_f = "23"

    def add(self, rate, time):
        tmp = [int_original(rate), time]
        self.rate_history.append(tmp)
        return self.getMyRate()

    def cancel(self):
        if len(self.rate_history) != 0:
            self.rate_history.pop()

    def calcSum(self):
        self.rate_sum = 0
        for rates in self.rate_history:
            self.rate_sum += rates[0]

    def getMyRate(self):
        self.calcSum()
        return self.rate_sum

    def getHistory(self):
        message = ""
        count = 0
        for add in self.rate_history:
            count += 1
            if add[0] > 0:
                tmp = "+"
            else :
                tmp = ""
            tmp = tmp + str(add[0])
            tmp = tmp + "\t[" + add[1].replace("\n", "") + "]\n"
            message = tmp + message
            if count == 10:
                break
        return message

    def reset(self):
        self.rate_history = []
        self.rate_sum = 0


MyTeam = Team()

@client.event
async def wait_until_login():
    printSysMessage("wait_until_login()が呼び出された．")

@client.event
async def on_ready():
    print( client.user.name )
    print( client.user.id )
    printSysMessage("ログインしました．")
    download()
    MyTeam.restore()
    updateManagers()
    printSystemInfo()
    channels = client.get_all_channels()
    for channel in channels:
        if "レート報告所" == channel.name:
            await client.send_message( channel, "【重要】ミニたるぽが再起動したゾ！\n最後のbackup以降のaddは保存されてないから，myrateなどで確認して復元するように！" )

@client.event
async def on_message(message):
    global act_bef
    global count
    channel_name = message.channel.name
    if channel_name is None:
        channel_name = "personal"
    if message.author.id != client.user.id and ( channel_name == "レート報告所" or channel_name == "personal" ):
        if channel_name == "personal":
            printSysMessage("DMからの送信")
        else :
            printSysMessage("レート報告所での送信")
        data = MessageProcessor(message)
        code = checkRegularCommand(data)
        if code == 1: # 正常処理
            printSysMessage( makeLog(data) )
            if data[0] == Commands[0]: # add
                tmp = str( MyTeam.addRate(data[1], data[2], data[3], data[4]) )
                if data[1] > 0:
                    reply = "+ "
                else :
                    reply = ""
                reply = reply + str(data[1]) + "，合計レート: " + tmp
                reply = "レートを追加したよ！おつぽりんこー\n" + reply
                act_bef = data
                # count += 1
                # if count == 10:
                upload(message)
                    # reply = reply + "\n【定期】レートをバックアップしたゾ"
                    # count = 0
                printSysMessage( "データを保存しました．" )
                MyTeam.save(message)
            elif data[0] == Commands[1]: # help
                reply = "<コマンドの一覧を表示するよ>\nadd :レートの増減を追加\nadd2 :レートの増減(ペア含む)を追加\nbackup：レート情報をバックアップ(レート終了時に忘れずやってね)\ncancel :１つ前のAddかAdd2を取り消すよ\nmyrate :自分の稼いだレートの合計を表示\nhistory :自分のレート増減履歴を表示\nteam :メンバーのレート情報を表示\ngraph :各メンバーのレートのグラフを表示\n\n<使い方の例を載せとくよ>\nadd 100\nadd @誰か(メンション) -25\nbackup\nhistory\n"
                printSystemInfo()
            elif data[0] == Commands[2]: # cancel
                tmp = cancel()
                if tmp == -1:
                    reply = "取り消す処理がないよ(ﾉД`)ｼｸｼｸ"
                elif tmp == 1:
                    reply = "１つ前のaddを取り消したよ．"
                else :
                    reply = "１つ前のadd2を取り消したよ．"
            elif data[0] == Commands[3]: # "myrate"
                tmp = str( MyTeam.getMemRate( data[1] ) )
                reply = "合計レート: " + tmp
            elif data[0] == Commands[4]: # team
                reply = MyTeam.getTeamInfo()
            elif data[0] == Commands[5]: # history
                reply = MyTeam.getHistory(data[1])
            elif data[0] == Commands[6]: # graph
                MyTeam.createGraph()
                with open(GRAPHPATH + "graph.png", 'rb') as graph:
                    await client.send_file(message.channel, graph)
                    return 0
            elif data[0] == Commands[7]: # save
                reply = "管理者権限がないよ(ﾉД`)ｼｸｼｸ"
                if isManager(data[1]):
                    MyTeam.save(message)
                    reply = "レートデータを保存したよ．"
            elif data[0] == Commands[8]: # restore
                reply = "管理者権限がないよ(ﾉД`)ｼｸｼｸ"
                if isManager(data[1]):
                    MyTeam.restore()
                    updateManagers()
                    reply = "レートデータを復元したよ．"
            elif data[0] == Commands[9]: # reset
                    reply = "管理者権限がないよ(ﾉД`)ｼｸｼｸ"
                    if isManager(data[1]):
                        MyTeam.reset()
                        reply = "これまでの情報をリセットしたよ．\nsaveで確定，restoreで修復ができるよ．"
            elif data[0] == Commands[10]: # manager
                    reply = "管理者権限がないよ(ﾉД`)ｼｸｼｸ"
                    if isManager(data[2]):
                        if not isManager(str(data[1])):
                            Managers.append(str(data[1]))
                            delSpace()
                            setManagers(message)
                            reply = "管理者の追加に成功！"
                        else :
                            reply = "その子もともと管理者やで．"
            elif data[0] == Commands[11]: # add2
                    MyTeam.addRate( data[2], data[3], data[4], data[5] )
                    MyTeam.addRate( data[2], str(data[1]), data[4], MyTeam.names[str(data[1])] )
                    reply = "レートの登録に成功したゾ．\nおつぽりんこ！\n" + MyTeam.getTeamInfo()
                    act_bef = data
                    # count += 1
                    # if count == 10:
                    upload(message)
                        # reply = reply + "\n【定期】レートをバックアップしたよん"
                        # count = 0
            elif data[0] == Commands[12]: # getfile
                reply = "送信が完了したよ．"
                if data[1] == Owner:
                    p = Path( SAVEPATH )
                    files = list(p.glob("*.txt"))
                    printSysMessage("以下のファイルを送信")
                    print( files )
                    print("-----------------------------------------------------------------")
                    for file in files:
                        f = open(str(file), 'rb')
                        await client.send_file(message.channel, f)
                        f.close()
            elif data[0] == Commands[13]: #backup
                reply = "バックアップをしたよ"
                upload(message)
            elif data[0] == Commands[14]: # download
                reply = "管理者権限がないよ(ﾉД`)ｼｸｼｸ．"
                if isManager(data[1]):
                    download()
                    reply = "レートデータをダウンロードしたよ"
            elif data[0] == Commands[15]: # del
                reply = "管理者権限がないよ(ﾉД`)ｼｸｼｸ．"
                if isManager( data[2] ):
                    reply = "" + MyTeam.delMember( data[1] )
                    reply = reply + "さんを削除したよ(ﾉД`)ｼｸｼｸ\n今までありがとう♡\n"
            else :
                reply = "??????"
            await client.send_message(message.channel, reply)
        else : # 適当に会話する
            name = str(message.author).split("#")[0]
            if name == "るなぴ":
                reply = Runapi[random.randint(0, len(Runapi)-1)]
            else :
                reply = Messages[ random.randint(0, len(Messages)-1) ]
            printSysMessage( makeLog(data) )
            await client.send_message(message.channel, reply)
    elif message.author.id != client.user.id and channel_name == "財宝通知":
        data = MessageProcessor( message )
        printSysMessage( makeLog(data) )
        if checkRegularCommand_zaihou( data ) :
            # 正常なコマンド
            reply = "aaa"
            if data[0] == Commands_Zaihou[0]: # 財宝
                reply = "@everyone おまいら財宝出たぞ！急げ！"
            elif data[0] == Commands_Zaihou[1]: # 時間設定
                reply = "ごめんまだ実装してない"
            await client.send_message(message.channel, reply)

def MessageProcessor(message): # 入力されたメッセージの前処理
    split_message = message.content.split()

    for i in range( len(split_message) ):
        split_message[i] = split_message[i].replace("–", "-")
        split_message[i] = split_message[i].replace("ー", "-")
        split_message[i] = split_message[i].replace("+", "")
        split_message[i] = split_message[i].replace("＋", "")
        split_message[i] = split_message[i].replace("@", "")
        split_message[i] = split_message[i].replace("<", "")

        split_message[i] = split_message[i].replace(">", "")

        if "-" in split_message[i]:
            split_message[i] = split_message[i].replace('-', '')
            if split_message[i].isdigit(): # 数値である
                split_message[i] = int_original(split_message[i])
                split_message[i] *= -1

        elif split_message[i].isdigit():
            split_message[i] = int_original(split_message[i])
    split_message.append(str(message.author.id))
    tmp = str(message.timestamp).split(" ")
    split_message.append( tmp[0] + "," + str( int_original( tmp[1].split(":")[0] ) + 9 ) + ":" +  tmp[1].split(":")[1] )
    split_message.append( str(message.author).split("#")[0] )
    return split_message

def checkRegularCommand(data):
    ReturnCode = 1 # 正常ならこのまま１を，違えばそれぞれのエラーコードを返す
    length = len(data)
    if length == 3:
        ReturnCode = 100
    elif data[0] not in Commands:
        ReturnCode = 200
    elif data[0] == Commands[0] and length != 5:
        ReturnCode = 310
    elif data[0] == Commands[0] and type(data[1]) is not int:
        ReturnCode = 320
    elif ( data[0] == Commands[10] or data[0] == Commands[15] ) and length != 5:
        ReturnCode = 330
    elif data[0] == Commands[10] and str(data[1]) not in MyTeam.members.keys():
        ReturnCode = 340
    elif data[0] == Commands[15] and str(data[1]) not in MyTeam.members.keys():
        ReturnCode = 340
    elif data[0] == Commands[11] and length != 6:
        ReturnCode = 350
    elif data[0] == Commands[11] and str(data[1]) not in MyTeam.members.keys():
        ReturnCode = 360
    elif data[0] == Commands[11] and type(data[1]) is not int:
        ReturnCode = 370
    elif data[0] not in [Commands[0], Commands[10], Commands[11], Commands[15]] and length > 4:
        ReturnCode = 400
    if ReturnCode != 1:
        print("[" + str(ReturnCode) + "]" + ERRORCODE[ReturnCode])
    return ReturnCode

def checkRegularCommand_zaihou( data ):
    return_bool = False
    length = len(data)
    if data[0] == "財宝" and length == 4:
        return_bool = True
    elif data[0] == "時間設定" and length == 6:
        return_bool = True
    return return_bool

def isManager(id):
    if id in Managers or str(id) in Managers:
        return True
    else :
        return False

def cancel():
    length = len(act_bef)
    if length == 5: # add
        MyTeam.cancel(act_bef[2])
        return 1
    elif length == 6: # add2
        MyTeam.cancel(str(act_bef[1]))
        MyTeam.cancel(act_bef[3])
        return 2
    else :
        return -1

def makeLog(data):
    if data[0] in Commands:
        reply = str(data[0]) + "の実行\n"
    if data[0] in Commands_Zaihou:
        reply = str(data[0]) + "の実行\n"

    else :
        reply = "コマンドが見つかりません．\n"
    for d in data:
        reply = reply + str(d) + ", "
    reply = reply + "\n-----------------------------------------------------------------"
    return reply

def upload(message):
    MyTeam.save(message)
    files = os.listdir( SAVEPATH )
    for file in files:
        if file[0] == ".":
            continue
        try :
            dbx.files_delete( DBX_SPATH + file )
        except :
            printSysMessage("削除ファイルが見つからない")
            print( DBX_SPATH + file )
            printFiles()
            pass
        f = open( SAVEPATH + file, "rb" )
        try :
            dbx.files_upload( f.read(), DBX_SPATH + file )
        except :
            printSysMessage("アップロード時のエラー")
            print( DBX_SPATH + file )
            pass
        f.close()
    with open( OTHERSPATH + "managers.txt", "rb" ) as f:
        dbx.files_delete( DBX_OPATH + "managers.txt" )
        dbx.files_upload( f.read(), DBX_OPATH + "managers.txt" )
    printSysMessage("セーブデータをアップロードしました．")

def delFiles():
    p = Path( SAVEPATH )
    files = list( p.glob("*.txt") )
    for file in files:
        os.remove( str(file) )

def download():
    delFiles()
    for entry in dbx.files_list_folder( DBX_SPATH ).entries:
        filename = str(entry.name)
        dbx.files_download_to_file( SAVEPATH + filename, DBX_SPATH + filename )
    dbx.files_download_to_file( OTHERSPATH + "managers.txt", DBX_OPATH + "managers.txt" )
    printSysMessage("セーブデータをダウンロードしました．")

def printSysMessage(message):
    print("[SystemMessage]" + message )

def setManagers(message):
    if not os.path.exists(OTHERSPATH):
        os.makedirs(OTHERSPATH, exist_ok=True)
    managers_data = ""
    for i in range(len(Managers)):
        managers_data = managers_data + str(Managers[i]) + ","
    with open( OTHERSPATH + "managers.txt", "w") as f:
        f.write(managers_data)

def printFiles():
    printSysMessage( DBX_SPATH +" ディレクトリのファイルリストを送信 ")
    for entry in dbx.files_list_folder( DBX_SPATH ).entries:
        print( DBX_SPATH + str(entry.name) )
    printSysMessage("-----------------------------------------------------------------")

def delSpace():
    while(1):
            try:
                Managers.remove("")
            except:
                break

def updateManagers():
    global Managers
    tmpdata = ""
    if os.path.exists( OTHERSPATH + "managers.txt" ):
        Managers = []
        with open( OTHERSPATH + "managers.txt", "r" ) as f:
            tmpdata = f.read()
        tmpdata = tmpdata.split(",")
        for d in tmpdata:
            if not isManager(d):
                Managers.append(d)
        delSpace()

def printSystemInfo():
    keys = list( MyTeam.members.keys() )
    printSysMessage("システム内情報を出力します．")
    print("Managers = ", end="")
    print(Managers)
    print("keys = ", end="")
    print( keys )
    print("names = ", end="[")
    MyTeam.update()
    for key in keys:
        print( MyTeam.names[key], end= ", " )
    print("]\nrates = ", end="[")
    for key in keys:
        print( MyTeam.rates[key], end = ", " )
    print("]")
    print("-----------------------------------------------------------------")

def int_original(message):
    returnNum = 0
    try :
        returnNum = int(message)
    except :
        returnNum = int(message[1:])
        print(message[0])
        if message[0] == "–":
            returnNum *= -1
        elif message[0] == "ー":
            returnNum *= -1
        else :
            returnNum *= 1
    return returnNum

client.run(TOKEN)
