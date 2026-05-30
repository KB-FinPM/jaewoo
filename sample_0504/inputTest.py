print ( "여러 줄 입력하세요 (끝내려면 Ctrl+D / Windows는 Ctrl+Z 후 Enter)" )
 
lines = []
while True :
    try :
        line = input ()
        lines.append ( line )
    except EOFError :
        break
 
multi_input = "\n".join ( lines )
 

print ( "입력 결과:" )
print ( multi_input )
