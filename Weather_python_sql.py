# Weather Data for Portal
import numpy as np
import calendar
from datetime import datetime as dt
from matplotlib.dates import num2date
import MySQLdb as dbapi

"""What needs to happen when entering WEATHER data:
Convert Julian day into two columns, month and day
make sure it converts correctly depending on if it is a leap year or not 
Save a copy of the edited data file as 'weathperiodcode'.csv
add data to the 'Hourly' database table
run a query to add daily data to 'Daily' table in database 
run a query to add monthly data to 'Monthly table in database"""

def import_datafile(filename):
    ''' imports data as a lists of lists with elements:  
0 = array, 1 = year, 2 = Julian day, 3 = hour, 4 = ppt, 5 = tempAir, 6 = RelHumid 
The length check makes sure NOT to import shorter rows, which are battery readings'''
    datafile = open(filename, 'r')
    data_list = []
    for row in datafile:
        row_data = row.strip().split(',')
        if len(row_data) == 7:
            row_data = map(float, row_data)
            data_list.append(row_data)
    return data_list
            
def add_tempSoil(data_line):
    '''adds an empty string to the data line. This will go in the tempSoil column later.'''
    return data_line.append(None)

def jday2caldates(data_line):
    '''takes a year and a julian day (range(0,366)) and returns a 
    calendar month and day. defines a list of months and days for both year types
    on which to index the julian day to calendar day and month.'''
    leapdays = sum([range(1,32), range(1,30), range(1,32), range(1,31), range(1,32), range(1,31),range(1,32), range(1,32), range(1,31),range(1,32), range(1,31),range(1,32)],[])
    leapmos = sum([[1]*31,[2]*29,[3]*31,[4]*30,[5]*31,[6]*30,[7]*31,[8]*31,[9]*30,[10]*31,[11]*30,[12]*31],[])
    days = sum([range(1,32), range(1,29), range(1,32), range(1,31), range(1,32), range(1,31),range(1,32), range(1,32), range(1,31),range(1,32), range(1,31),range(1,32)],[])
    months = sum([[1]*31,[2]*28,[3]*31,[4]*30,[5]*31,[6]*30,[7]*31,[8]*31,[9]*30,[10]*31,[11]*30,[12]*31],[])
    if calendar.isleap(data_line[1])==True:
        cal_day = leapdays[int(data_line[2]) - 1]
        cal_month = leapmos[int(data_line[2]) - 1]
        data_line.extend([cal_month, cal_day])
        return data_line
    else :
        cal_day = days[int(data_line[2]) - 1]
        cal_month = months[int(data_line[2]) - 1]
        data_line.extend([cal_month, cal_day])
        return data_line

def rearrange_cols(data_line):
    '''where order of data_line is: 
    array, year, julianDay, hour, ppt, tempAir, relHumid, tempSoil, month, day
    and we want:
    Year, Month, Day, Hour, TempAir, RelHumid, TempSoil, Precipitation(mm)
    array and julianDay are left out because they are not necessary for the weather dataset.'''
    myorder = [1, 8, 9, 3, 5, 6, 7, 4] 
    data_line = [data_line[i] for i in myorder]
    return data_line
    
def prepare_data_row(data_line):
    '''inputs a line of data from weather.dat and determines if it's a battery reading.
    If not, then  the dataline is manipulated and appended to fit the Portal weather database.'''
    add_tempSoil(data_line)
    data_line = jday2caldates(data_line)
    data_line = rearrange_cols(data_line)
    return data_line
    
def compile_weather_data(data):
    '''input weather.dat file. 
    Columns are: array | year | Julian day | hour | ppt | tempAir | RelHumid
    Reads the data into the prepare_data function line by line, determining if 
    the data is a battery reading, in which case it is not added to the new
    list of weather data to be appended to the database.'''
    weather_data = []
    for line in weather:
        wx = prepare_data_row(line)
        weather_data.append(wx)
    return weather_data
            
def save_weather_file(data, filename):
    '''saves weather as a csv file to a shared location. input the new datafile
    and a string that has the name and extension of the file to which is should be 
    saved.'''
    weatherFile = open(filename,'wb') 
    w = csv.writer(weatherFile,delimiter=',')
    w.writerows(data)
    weatherFile.close()

    
# Execute commands if running directly:    
if __name__ == '__main__':
    
#location of new weather file;  For example, use 'F:\AdvProj_Portal\Met395.dat'
    filename = input('Where is your most recent weather file located? (Example: "pathname\MET397.dat")')
    weather = import_datafile(filename)

    weather_to_add = compile_weather_data(weather)
    

    #DATABASE STUFF: open file to append to database
    user = input('What is your username?: ')
    yourpassword = input('Please enter your password: ')

    con = dbapi.connect(host = 'serenity.bluezone.usu.edu',
              port = 1995,
              user = user,
              passwd = yourpassword)

    cur = con.cursor()

    # create and fill table with new weather data
    cur.execute("USE Hourlyweather")
    cur.execute("DROP TABLE IF EXISTS weath")
    cur.execute("""CREATE TABLE queries.weath
    ( Year DOUBLE,
    Month DOUBLE,
    Day DOUBLE, 
    Hour DOUBLE, 
    TempAir FLOAT
    RelHumid FLOAT
    TempSoil FLOAT
    Precipiation(mm) FLOAT
    )""")

    cur.execute("""LOAD DATA LOCAL INFILE weather_to_add
    INTO TABLE queries.weath
    FIELDS TERMINATED BY ',' ENCLOSED BY '"'
    IGNORE 0 LINES""")

    #append data to Hourly weather Table, making sure not to repeat data that already exists
    cur.execute("""INSERT INTO Portal.Hourlyweather SELECT weath.* 
    FROM queries.weath
    LEFT JOIN queries.weath ON Hourlyweather.year = weath.year, Hourlyweather.month = weath.month,
    Hourlyweather.day = weath.day, Hourlyweather.hour = weath.hour
    WHERE Hourlyweather.* IS NULL and weath.* <>''""") #how do I do this?
    con.commit()
    
    #numrows = RETURN THE NUMBER OF UNMATCHED ROWS THAT WERE APPENDED

    # run a query to add daily data to 'Daily' table in database 
    cur.execute("""SELECT DISTINCTROW HourlyWeather.Year, HourlyWeather.Month, HourlyWeather.Day, 
    Avg(HourlyWeather.TempAir) AS TempAirAvg, Max(HourlyWeather.TempAir) AS TempAirMax, 
    Min(HourlyWeather.TempAir) AS TempAirMin, Avg(HourlyWeather.RelHumid) AS RH_Avg, 
    Max(HourlyWeather.RelHumid) AS RH_Max, Min(HourlyWeather.RelHumid) AS RH_Min, 
    Avg(HourlyWeather.TempSoil) AS TempSoilAvg, Max(HourlyWeather.TempSoil) AS TempSoilMax, 
    Min(HourlyWeather.TempSoil) AS TempSoilMin, Sum(HourlyWeather.Precipitation(mm)) AS Total_Precipitation
    INSERT INTO Daily(mm)
    FROM HourlyWeather
    GROUP BY HourlyWeather.Year, HourlyWeather.Month, HourlyWeather.Day""")
    
    # run a query to add monthly data to 'Monthly' table in database
    cur.execute("""SELECT DISTINCTROW HourlyWeather.Year, HourlyWeather.Month, Avg(HourlyWeather.TempAir) 
    AS TempAirAvg, Max(HourlyWeather.TempAir) AS TempAirMax, Min(HourlyWeather.TempAir) AS TempAirMin, 
    Avg(HourlyWeather.RelHumid) AS RH_Avg, Max(HourlyWeather.RelHumid) AS RH_Max, 
    Min(HourlyWeather.RelHumid) AS RH_Min, Avg(HourlyWeather.TempSoil) AS TempSoilAvg, 
    Max(HourlyWeather.TempSoil) AS TempSoilMax, Min(HourlyWeather.TempSoil) AS TempSoilMin, 
    Sum(HourlyWeather.Precipitation(mm)) AS Total_Precipitation 
    INSERT INTO Monthly(mm)1989-present
    FROM HourlyWeather
    GROUP BY HourlyWeather.Year, HourlyWeather.Month""")

    con.commit()
    print 'Project complete. You have appended, ', numrows, 'to the weather data on Serenity.'
    