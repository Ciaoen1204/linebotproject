a=float(input("請輸入體溫:"))
b=int(input("請輸入測量方式:"))
if b==1:
    if 36.6<=a<=38:
        print("體溫正常")
    else:
        print("體溫異常")
elif b==2:
    if 35.7<=a<=38:
        print("體溫正常")
    else:
        print("體溫異常")
elif b==3:
    if 35.5<=a<=37.5:
        print("體溫正常")
    else:
        print("體溫異常")
elif b==4:
    if 35.0<=a<=37.5:
        print("體溫正常")
    else:
        print("體溫異常")
else:
    if 34.7<=a<=37.3:
        print("體溫正常")
    else:
        print("體溫異常")
