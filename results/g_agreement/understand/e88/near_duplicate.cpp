#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <vector>
using namespace std;
uint32_t word(ifstream& f){uint32_t x;f.read((char*)&x,4);if(!f)throw 1;return x;}
using Text=vector<uint32_t>;
int distance_bounded(const Text&a,const Text&b,int k){
 int n=a.size(),m=b.size();if(abs(n-m)>k)return k+1;
 int p=0;while(p<n&&p<m&&a[p]==b[p])++p;
 while(n>p&&m>p&&a[n-1]==b[m-1]){--n;--m;}n-=p;m-=p;
 if(!n)return m;if(!m)return n;
 vector<int> prev(m+1,k+1),cur(m+1,k+1);
 for(int j=0;j<=min(m,k);++j)prev[j]=j;
 for(int i=1;i<=n;++i){fill(cur.begin(),cur.end(),k+1);if(i<=k)cur[0]=i;int low=k+1;
  for(int j=max(1,i-k);j<=min(m,i+k);++j){cur[j]=min({prev[j]+1,cur[j-1]+1,prev[j-1]+int(a[p+i-1]!=b[p+j-1])});low=min(low,cur[j]);}
  if(low>k)return k+1;swap(prev,cur);
 }return prev[m];
}
int main(int argc,char**argv){if(argc!=3)return 2;ifstream f(argv[1],ios::binary);int n=word(f),m=word(f);vector<Text>xs(n+m);
 for(auto&x:xs){x.resize(word(f));f.read((char*)x.data(),x.size()*4);if(!f)return 3;}
 ofstream o(argv[2]);for(int i=0;i<n;++i)for(int j=0;j<m;++j){int l=max(xs[i].size(),xs[n+j].size());int k=(l-1)/10;if(l==0){o<<i<<' '<<j<<" 0\n";continue;}int d=distance_bounded(xs[i],xs[n+j],k);if(d<=k)o<<i<<' '<<j<<' '<<d<<'\n';}return 0;
}
