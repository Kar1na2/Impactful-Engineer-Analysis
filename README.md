# Impactful-Engineer-Analysis

## **Problem** 

[PostHog](https://github.com/PostHog/posthog), an open-source company that manages an all-in-one analytics sdk, has a total of 527 contributors (including 2 posthog bot's and Claude). The contributions throughout the past 90 days was reported on Github as this picture.

![commits graph](images/Commits%20over%20time.png)


Despite the many contributions being made by numerous engineers, it is hard to know who really made an **impact** for PostHog as simple metrics such as lines of code, amounts of commits, etc. don't tell the full story. 

## **Solution** 

I'll be getting the top 5 **impactful** engineers through the following procedure

1. **Product trends:** Regardless of how impressive an engineer's contribution might have been, if it's not equally useful or impressive to the eyes of the customer, then it does not have an impact 
    - This will be measured through looking at download trends from npm and python, spike in increase in downloads / dips and looking at the correlating updates made onto PostHog

2. **Filtering Engineers:** If there was a noticable correlation between an update and the increase in downloads then I'll look at the engineers that collaborated in that update 
    - If there are no noticable correlations, then I'll be moving onto step 3 and put a little more emphasis on Issues / PRs made during that time period instead

3. **Impact measurement:** Simply measuring an engineer's worth by looking at amount of lines they contributed to the update is overestimating the actual impact, so I'll be now measuring impact in the lens of an another engineer 
    - Github Issues, PRs, and the commits associated to those PRs will be the primarily source of data 
    - From those data I'll be taking a look at the contents, specifically: 
        - When making an Issue or a PR was the problem identified concretely
        - When addressing a solution was it equally made concretely for an another engineer to pick up on 
        - Does the commit message properly encapsulate the changes made
    - With these measurements I'll look at who primarily contributed most in that update as well as who identified the problem and solution properly.

4. **Notable exceptions:** Engineers who made contributions in streamlining the development or adding additional railguards will be considered as exceptions since although the customers won't be noticing the contributions, the impact in future development for any new or pre-existing engineers should be acknowledged
    - PostHog also have 2 difference SDKs one for npm and another for Python Package, it is best to separate the engineers that worked on the npm in contrast to working on the Python Package

## **Data** 

From [npmtrends.com](https://npmtrends.com/posthog-js-vs-posthog-node), the graph looked like 

![npm graph](images/npm%20Posthog%20trend.png)

and from the python trend using pypistats (json downloaded as "posthog_downloads.json") 

for reproducability the following bash script was ran for the data 
```bash 
pypistats overall posthog --start-date 2026-04-07 --end-date 2026-07-06 --daily --format json > posthog_downloads.json
```

![python graph](images/Python%20PostHog%20Graph.png)

**Notable dates** 
- May 17 - 31st showed a decline in npm downloads 
- May 31st - June 14 showed a sharp incline in npm downloads before stagnating
- June 13 - June 17 showed a growth rate in Python SDK downloads
- June 25 - June 28 showed another increase in growth rate 

## **Results** 

Being short on time, I used Claude to do most of the heavy lifting with the website generation, etc and published the [website](https://kar1na2.github.io/Impactful-Engineer-Analysis/) as a static webpage using Github Pages

My notes on the correlation of events and dates as well as issues I ran into has been noted down in `personal notes.md`

Also using Claude, I have generated the scoring system, methodology, as well as reproducability all in `Details.md`

## **Things to improve on**

A metric I wanted to utilize the most was the details in an engineer's PR, their Github Issue post, their commit messages. However, taking into consideration every single Issue posted, every single commit made took up too much time. I can remove the need of analyzing each commit and focus on the bigger picture with the PR although a fear is that I'll be crediting too much or discrediting by losing the specificity. 

An alternate solution I'm thinking of is instead of going from bottom up, I instead look from top to bottom with looking at the version releases then looking at the time period between a version and the next version and seeing if it changed the general trend for customer usage (this will impact the weight of the contribution a bit). Then I will look at the engineers that contributed for that version release and categorize them on what they have specifically worked on. Afterwards, I would accumulate each engineer's contribution and then rank them based on how many releases they were part of and how much impact they had for each release. 

I also failed to acknowledge the exceptions I have noted down earlier, a separate filtering to accomodate for that exception will also help improve my analysis to be more accurate in determining the **impact** engineers had on PostHog.

## **Time**

This is a screenshot of the timer I had running in the background while working on this project

![alt text](Images/Timer.png)

1 hour 32 minutes and 53 seconds is when I stopped the timer, wrapping up the *Things to improve on* section as well as this costed me around 2-3 more minutes.